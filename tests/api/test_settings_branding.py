"""API tests for branding settings endpoints."""

from pathlib import Path


def test_get_branding_settings_returns_defaults(client):
    resp = client.get('/api/settings/branding')
    assert resp.status_code == 200
    data = resp.json()
    assert data['companyName']
    assert data['headerLogoUrl']


def test_update_branding_settings_requires_admin(client):
    csrf = client.get('/api/csrf-token').json()['token']
    resp = client.put(
        '/api/settings/branding',
        json={'companyName': 'Meine Firma'},
        headers={'X-CSRF-Token': csrf},
    )
    assert resp.status_code == 401


def test_update_branding_settings_as_admin(admin_client):
    resp = admin_client.put(
        '/api/settings/branding',
        json={'companyName': 'Meine Testfirma GmbH'},
        headers={'X-CSRF-Token': admin_client.csrf_token},
    )
    assert resp.status_code == 200

    check = admin_client.get('/api/settings/branding')
    assert check.status_code == 200
    assert check.json()['companyName'] == 'Meine Testfirma GmbH'


def test_upload_branding_logo_as_admin(admin_client):
    logo_svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="30"></svg>'
    resp = admin_client.post(
        '/api/settings/branding/logo',
        files={'file': ('brand-test.svg', logo_svg, 'image/svg+xml')},
        headers={'X-CSRF-Token': admin_client.csrf_token},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload['headerLogoUrl'].startswith('/images/company-logo-custom')

    logo_path = Path(__file__).resolve().parents[2] / 'wwwroot' / 'images' / 'company-logo-custom.svg'
    if logo_path.exists():
        logo_path.unlink()
