import os
from glob import glob
import subprocess
import sys

# Instalar dependencias si no están presentes
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import yaml
except ImportError:
    install("pyyaml")
    import yaml

try:
    import requests
except ImportError:
    install("requests")
    import requests


ACCESS_TOKEN = os.getenv("token")
ADMIN_URL = os.getenv("adminURL")
APPS_DIR = '/apps'
HEADERS = {'Authorization': f'Bearer {ACCESS_TOKEN}'}

def load_applications():
    applications = []
    for file in glob(f"{APPS_DIR}/*.yaml"):
        with open(file) as f:
            app_data = yaml.safe_load(f)
            applications.append(app_data)
    return applications

def get_accounts():
    url = f"{ADMIN_URL}/admin/api/accounts.json?access_token={ACCESS_TOKEN}&page=1&per_page=500"
    headers = {
        "accept": "*/*"
    }

    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    accounts = []
    data = response.json()

    for item in data.get("accounts", []):
        account = item["account"]
        accounts.append({
            "id": account["id"],
            "org_name": account["org_name"]
        })

    return accounts

def application_exists(app_user_key):
    url = f"{ADMIN_URL}/admin/api/applications/find.xml?user_key={app_user_key}"
    response = requests.get(url, auth=(ACCESS_TOKEN, ''), verify=False)
    return response.status_code == 200

def create_application(app, accounts):
    account_id = next((a['account']['id'] for a in accounts if a['account']['org_name'] == app['account']), None)
    if not account_id:
        print(f"No se encontró cuenta para la app {app['app_name']}")
        return

    url = f"{ADMIN_URL}/admin/api/accounts/{account_id}/applications.json"
    data = {
        "name": app["app_name"],
        "description": app.get("description", ""),
        "plan_id": app["plan_id"],
        "application_id": app["app_id"],
        "user_key": app["app_user_key"],
        "redirect_url": app.get("redirect_url", ""),
    }
    response = requests.post(url, headers=HEADERS, json={"application": data}, verify=False)

    if response.status_code == 201:
        print(f"✅ Aplicación creada: {app['app_name']}")
    elif response.status_code == 409:
        print(f"ℹ️ Aplicación ya existe: {app['app_name']}")
    else:
        print(f"❌ Error al crear app {app['app_name']}: {response.status_code} - {response.text}")

def main():
    applications = load_applications()
    accounts = get_accounts()

    for app in applications:
        if application_exists(app['app_user_key']):
            print(f"EXISTE: {app['app_name']}")
        else:
            create_application(app, accounts)

if __name__ == '__main__':
    main()