with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Hashea contraseñas en memoria para evitar incompatibilidades
config["credentials"] = stauth.Hasher.hash_passwords(config["credentials"])

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
    auto_hash=False,
)