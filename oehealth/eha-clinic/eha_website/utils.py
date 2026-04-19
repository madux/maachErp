def get_payment_providers_details(request):
    enabled_payment_provider = request.env['ir.config_parameter'].sudo(
    ).get_param('eha_website.custom_payment_provider', '')

    payment_provider = request.env['payment.provider'].sudo().search([('code', '=', enabled_payment_provider)])

    if enabled_payment_provider == "rave":
        public_key = payment_provider.rave_public_key
        secret_key = payment_provider.rave_secret_key
    else:
        public_key = payment_provider.paystack_public_key
        secret_key = payment_provider.paystack_secret_key

    return {"provider": payment_provider.code, "public_key": public_key, "secret_key": secret_key}
