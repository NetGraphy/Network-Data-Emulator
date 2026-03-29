"""Capture screenshots of the SNEP platform for documentation."""

import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://snep-frontend-staging.up.railway.app"
OUT = "/Users/jasonmercer/Code/Network-Data-Emulator/docs/screenshots"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="dark",
        )
        page = await ctx.new_page()

        # 1. Topology
        print("Capturing topology...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUT}/01-topology.png")

        # 2. Devices list
        print("Capturing devices...")
        await page.goto(f"{BASE_URL}/devices", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/02-devices.png")

        # 3. Device detail - CLI Preview
        print("Capturing device detail...")
        await page.goto(f"{BASE_URL}/devices/c3d4e5f6-0003-0003-0003-000000000001", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        # Click CLI Preview tab
        cli_tab = page.locator("button", has_text="CLI Preview")
        if await cli_tab.count() > 0:
            await cli_tab.click()
            await page.wait_for_timeout(500)
            # Select show version
            select = page.locator("select").first
            await select.select_option("show version")
            await page.wait_for_timeout(500)
            # Click Execute
            execute = page.locator("button", has_text="Execute")
            if await execute.count() > 0:
                await execute.click()
                await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{OUT}/03-cli-preview.png")

        # 4. Device detail - SNMP
        print("Capturing SNMP walk...")
        snmp_tab = page.locator("button", has_text="SNMP")
        if await snmp_tab.count() > 0:
            await snmp_tab.click()
            await page.wait_for_timeout(1000)
            # Click SNMP Walk
            walk_btn = page.locator("button", has_text="SNMP Walk")
            if await walk_btn.count() > 0:
                await walk_btn.click()
                await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{OUT}/04-snmp-walk.png")

        # 5. CLI Modeling
        print("Capturing CLI modeling...")
        await page.goto(f"{BASE_URL}/cli-modeling", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/05-cli-modeling.png")

        # 6. Scenarios
        print("Capturing scenarios...")
        await page.goto(f"{BASE_URL}/scenarios", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        # Click first scenario
        scenario_btn = page.locator("button", has_text="Uplink Failure")
        if await scenario_btn.count() > 0:
            await scenario_btn.click()
            await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/06-scenarios.png")

        # 7. Custom Filters
        print("Capturing custom filters...")
        await page.goto(f"{BASE_URL}/custom-filters", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        # Click first filter
        filter_btn = page.locator("button", has_text="bits_to_human")
        if await filter_btn.count() > 0:
            await filter_btn.click()
            await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/07-custom-filters.png")

        # 8. Query Explorer
        print("Capturing query explorer...")
        await page.goto(f"{BASE_URL}/query-explorer", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/08-query-explorer.png")

        # 9. Settings
        print("Capturing settings...")
        await page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/09-settings.png")

        # 10. Connection Info
        print("Capturing connection info...")
        await page.goto(f"{BASE_URL}/devices/c3d4e5f6-0003-0003-0003-000000000001", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        conn_tab = page.locator("button", has_text="Connection Info")
        if await conn_tab.count() > 0:
            await conn_tab.click()
            await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/10-connection-info.png")

        await browser.close()
        print(f"\nAll screenshots saved to {OUT}/")


if __name__ == "__main__":
    asyncio.run(main())
