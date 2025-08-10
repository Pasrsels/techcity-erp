import requests

url = "https://zimra.co.zw/Device/v1/23265/getConfig"
headers = {
    "DeviceModelName": "Server",
    "DeviceModelVersionNo": "v1"
}

cert = ("device_cert.pem", "device_key.pem")
response = requests.get(url, headers=headers, cert=cert, verify="zimra_ca_bundle.crt")
print(response.json())
