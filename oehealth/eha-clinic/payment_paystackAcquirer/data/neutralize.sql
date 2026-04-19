-- disable paystack payment provider
UPDATE payment_provider
   SET paystack_public_key = NULL,
       paystack_secret_key = NULL,
       paystack_webhook_secret = NULL;
