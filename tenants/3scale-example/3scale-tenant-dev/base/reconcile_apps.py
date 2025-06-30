import os
from glob import glob
import subprocess
import sys
import json

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

def get_service_id_by_system_name(system_name):
    url = f"{ADMIN_URL}/admin/api/services.json?access_token={ACCESS_TOKEN}&per_page=500"
    response = requests.get(url, headers={"accept": "*/*"}, verify=False)
    response.raise_for_status()

    for item in response.json().get("services", []):
        service = item["service"]
        if service["system_name"] == system_name:
            return service["id"]

    raise ValueError(f"❌ No se encontró servicio con system_name '{system_name}'")

def get_plan_id_by_name(service_id, plan_name):
    url = f"{ADMIN_URL}/admin/api/services/{service_id}/application_plans.json?access_token={ACCESS_TOKEN}"
    response = requests.get(url, headers={"accept": "*/*"}, verify=False)
    response.raise_for_status()

    for item in response.json().get("plans", []):
        plan = item["application_plan"]
        if plan["name"] == plan_name:
            return plan["id"]

    raise ValueError(f"❌ No se encontró plan '{plan_name}' para servicio {service_id}")

def create_application(app, accounts):
    account_id = next((a['id'] for a in accounts if a['org_name'] == app['account']), None)
    if not account_id:
        print(f"No se encontró cuenta para la app {app['app_name']}")
        return
    if "plan_id" not in app:
        service_id = get_service_id_by_system_name(app["service_system_name"])
        plan_id = get_plan_id_by_name(service_id, app["application_plan_name"])
    else:
        plan_id = app["plan_id"]

    user_key = app.get("app_user_key", app["application_id"])

    payload = {
        "name": app["app_name"],
        "description": app.get("description", ""),
        "plan_id": plan_id,
        "application_id": app["application_id"],
        "user_key": user_key,
        "application_key": app["application_key"],
        "redirect_url": app.get("redirect_url", ""),
        "access_token": ACCESS_TOKEN
    }

    url = f"{ADMIN_URL}/admin/api/accounts/{account_id}/applications.json"


    print("\n➡️ Payload que se va a enviar:")
    print(json.dumps(payload, indent=2))
    print(f"➡️ URL: {url}")
    print(f"➡️ Headers: {HEADERS}")
    response = requests.post(url, headers={"accept": "*/*"}, json={"application": payload}, verify=False)

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
        if application_exists(app.get("user_key", app["application_id"])):
            print(f"EXISTE: {app['app_name']}")
        else:
            create_application(app, accounts)

if __name__ == '__main__':
    main()