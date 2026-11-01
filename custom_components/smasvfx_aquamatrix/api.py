"""AQUAmatrix SMASVFX API Client with MFA Support."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientResponse, ClientSession


class SMASVFXClient:
    """Client for AQUAmatrix SMASVFX web portal."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        tenant: str,
        username: str,
        password: str,
        logger: logging.Logger,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._base = base_url.rstrip("/")
        self._tenant = tenant.strip("/")
        self._username = username
        self._password = password
        self._logger = logger
        self._rvt: str | None = None

    def _url(self, path: str) -> str:
        """Construct a full URL for the given path."""
        return f"{self._base}/{self._tenant}/{path.lstrip('/')}"

    async def _fetch(self, method: str, url: str, **kwargs: Any) -> tuple[ClientResponse, str]:
        """Perform an HTTP request and return the response and body."""
        self._logger.debug("SMASVFX %s %s", method, url)
        async with self._session.request(method, url, **kwargs) as resp:
            text = await resp.text()
            self._logger.debug("SMASVFX %s %s -> %s head=%s", method, url, resp.status, text[:250])
            return resp, text

    async def _get_login_page(self) -> tuple[str, str]:
        """Retrieve the login page and its URL."""
        login_url = self._url("Account/Login")
        headers = {"User-Agent": "HomeAssistant", "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"}
        resp, text = await self._fetch("GET", login_url, headers=headers)
        if resp.status >= 400:
            raise Exception(f"Login GET failed: {resp.status}")
        return login_url, text

    def _parse_login_form(self, base_url: str, html: str) -> tuple[str, dict[str, str], str, str]:
        """Parse the login form to extract the action URL and fields."""
        form_re = re.compile(
            r'<form[^>]*method=["\\\']?post["\\\']?[^>]*>(.*?)</form>', re.I | re.S
        )
        mform = form_re.search(html)
        if not mform:
            raise Exception("Login form not found")
        form_html = mform.group(0)
        action_m = re.search(r'action=["\\\']([^"\\\']*)["\\\']', form_html, re.I)
        action = action_m.group(1) if action_m else ""
        action_url = urljoin(base_url, action) if action else base_url
        inputs = re.findall(r"<input[^>]*>", form_html, re.I)
        data: dict[str, str] = {}
        username_candidates: list[str] = []
        password_name: str | None = None
        for inp in inputs:
            name_m = re.search(r'name=["\\\']([^"\\\']+)["\\\']', inp, re.I)
            if not name_m:
                continue
            name = name_m.group(1)
            type_m = re.search(r'type=["\\\']([^"\\\']+)["\\\']', inp, re.I)
            itype = type_m.group(1).lower() if type_m else "text"
            val_m = re.search(r'value=["\\\']([^"\\\']*)["\\\']', inp, re.I)
            value = val_m.group(1) if val_m else ""
            if "__RequestVerificationToken" in name:
                data[name] = value
                continue
            if itype == "password":
                password_name = name
                continue
            if itype == "hidden":
                data[name] = value
                continue
            username_candidates.append(name)

        user_field = "UserCode" if "UserCode" in username_candidates else (username_candidates[0] if username_candidates else "Email")
        if password_name is None:
            password_name = "Password"

        data[user_field] = self._username
        data[password_name] = self._password
        if "RememberMe" in (n for n in data) or "RememberMe" in html:
            data["RememberMe"] = "true"

        self._logger.debug(
            "SMASVFX login form: action=%s user_field=%s pass_field=%s",
            action_url,
            user_field,
            password_name,
        )
        return action_url, data, user_field, password_name

    async def login(self) -> str:
        """Perform login and trigger email MFA code."""
        login_url, html = await self._get_login_page()
        action_url, data, _, _ = self._parse_login_form(login_url, html)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self._base,
            "Referer": login_url,
            "User-Agent": "HomeAssistant",
        }
        resp, text = await self._fetch(
            "POST", action_url, data=data, headers=headers, allow_redirects=True
        )
        if resp.status >= 400:
            raise Exception(f"Login POST failed: {resp.status}")

        final_url = str(resp.url)
        self._logger.debug("SMASVFX login final_url: %s", final_url)

        if "VerifyCode" in final_url or "Código" in text or "Confirm" in text or "Verification" in text:
            self._logger.info("SMASVFX MFA verification code triggered.")
            return "mfa_required"

        try:
            await self._refresh_page_token()
            return "success"
        except Exception:
            return "mfa_required"

    async def verify_mfa(self, code: str) -> bool:
        """Submit the email verification MFA code."""
        verify_url = self._url("Account/VerifyCode")
        headers = {"User-Agent": "HomeAssistant", "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"}

        resp, text = await self._fetch("GET", verify_url, headers=headers)

        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', text, re.I)
        token = m.group(1) if m else (self._rvt or "")

        payload = {
            "__RequestVerificationToken": token,
            "Code": code,
        }
        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self._base,
            "Referer": verify_url,
            "User-Agent": "HomeAssistant",
        }
        resp, text = await self._fetch(
            "POST", verify_url, data=payload, headers=post_headers, allow_redirects=True
        )
        self._logger.debug("SMASVFX verify_mfa post status=%s final_url=%s", resp.status, resp.url)

        if resp.status >= 400:
            return False

        try:
            await self._refresh_page_token()
            return True
        except Exception:
            return not ("inválid" in text.lower() or "incorreto" in text.lower())

    def _extract_cookie_token(self) -> str | None:
        """Extract the request verification token from cookies."""
        jar = self._session.cookie_jar
        for cookie in jar:
            if cookie.key.startswith("__RequestVerificationToken"):
                return cookie.value
        return None

    async def _refresh_page_token(self) -> str:
        """Refresh the page verification token."""
        url = self._url("ReadingsAndConsumptions")
        resp, text = await self._fetch("GET", url, headers={"User-Agent": "HomeAssistant"})
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', text, re.I)
        if m:
            self._rvt = m.group(1)
        return self._rvt or ""

    def _ajax_headers(self, referer_path: str, pair_tokens: bool = False) -> dict[str, str]:
        """Prepare AJAX headers for API requests."""
        ref = self._url(referer_path)
        rvt = self._rvt or ""
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/plain, */*",
            "Referer": ref,
            "User-Agent": "HomeAssistant",
        }
        if rvt:
            if pair_tokens:
                cookie_tok = self._extract_cookie_token() or ""
                value = f"{rvt}:{cookie_tok}" if cookie_tok else rvt
                headers["RequestVerificationToken"] = value
                headers["X-RequestVerificationToken"] = value
            else:
                headers["RequestVerificationToken"] = rvt
                headers["X-RequestVerificationToken"] = rvt
        return headers

    async def _get_json_once(self, path: str, referer_path: str, pair_tokens: bool) -> Any:
        """Perform a single JSON fetch attempt."""
        url = self._url(path)
        headers = self._ajax_headers(referer_path, pair_tokens=pair_tokens)
        self._logger.debug("SMASVFX GET %s (pair=%s)", url, pair_tokens)
        async with self._session.get(url, headers=headers) as resp:
            text = await resp.text()
            self._logger.debug("SMASVFX GET %s status=%s head=%s", path, resp.status, text[:200])
            if resp.status != 200:
                raise Exception(f"GET {path} failed: {resp.status}; head={text[:200]}")
            try:
                return await resp.json(content_type=None)
            except Exception:
                return json.loads(text)

    async def _get_json(self, path: str, referer_path: str) -> Any:
        """Get JSON with token refresh and login retry if needed."""
        try:
            return await self._get_json_once(path, referer_path, pair_tokens=False)
        except Exception as e1:
            self._logger.debug("SMASVFX first GET failed: %s", e1)
            await self._refresh_page_token()
            try:
                return await self._get_json_once(path, referer_path, pair_tokens=True)
            except Exception:
                login_result = await self.login()
                if login_result == "mfa_required":
                    raise Exception("MFA challenge triggered during runtime. Re-authentication requires a verification code.")
                return await self._get_json_once(path, referer_path, pair_tokens=True)

    async def _try_paths(self, paths: list[str], referer_path: str) -> Any:
        """Try multiple paths sequentially until one succeeds."""
        last_exc: Exception | None = None
        for p in paths:
            try:
                return await self._get_json(p, referer_path)
            except Exception as e:
                last_exc = e
                self._logger.debug("SMASVFX path failed %s -> %s", p, e)

        # If all paths failed because of an MFA trigger or session expiry, chain it here:
        if last_exc and "MFA" in str(last_exc):
            raise Exception("MFA challenge triggered during runtime.") from last_exc

        raise last_exc or Exception("All paths failed")

    async def get_last_reading(self) -> Any:
        """Retrieve the last meter reading."""
        return await self._try_paths(
            ["ReadingsAndConsumptions/GetLastReadingInfo", "Readings/GetLastReadingInfo"],
            "ReadingsAndConsumptions",
        )

    async def get_consumptions_graph(self) -> Any:
        """Retrieve the consumption graph data."""
        return await self._try_paths(
            ["ReadingsAndConsumptions/GetConsumptionsGraph", "Readings/GetConsumptionsGraph"],
            "ReadingsAndConsumptions",
        )

    async def get_billed_graph(self) -> Any:
        """Retrieve the billing graph data."""
        return await self._get_json("Billing/GetBilledValuesGraph", "Home/Index")

    async def get_billing_info(self) -> Any:
        """Retrieve billing and debt information."""
        return await self._get_json("Billing/GetBillingInfo", "Home/Index")



