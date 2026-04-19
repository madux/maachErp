# Geoserver Setup

## Adding odoo for a new project
1. Use terraform to set up environment
2. Add project to `scripts/deploy.sh`
3. Build and deploy

## Building

```shell
docker-compose build
```

## Deploying

```shell
scripts/deploy.sh
```

## Running locally

```
docker-compose up -d
```

Once all services are started, test by visiting the odoo landing
page in your browser: [http://localhost:8069](http://localhost:8069).

