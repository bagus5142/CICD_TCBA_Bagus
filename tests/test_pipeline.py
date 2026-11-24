from function_app import API_BASE_URL

def test_api_url_configured():
    assert API_BASE_URL.startswith("https://")
    assert "upload-data-hotel.duckdns.org" in API_BASE_URL