# ehealth
This repo is a collection of Odoo modules that together provide features to manage patient information for the eHA clinic. The core module is [oehealth](https://www.odoo.com/apps/modules/11.0/oehealth/), an Odoo third party Electronic Medical Record module. Other modules provide added functionality for two factor authentication, audit trails and providing additional fields for patient names.

## Modules
- [oehealth](https://www.odoo.com/apps/modules/11.0/oehealth/): A third-party EMR module for managing patient information
- [partner_firstname](https://www.odoo.com/apps/modules/11.0/partner_firstname/): A third-party module for providing additional name fields (first name and last name) for patients
- [second_last_name](https://www.odoo.com/apps/modules/11.0/partner_second_lastname/): Extends the partner_firstname module and provides additional capability to add middlename fields when registering patients.
- [Two factor authentication](https://www.odoo.com/apps/modules/11.0/two_factor_authentication/): A third-party module that provides added functionality to enable two-factor authentication for all users
- [Audit Log](https://www.odoo.com/apps/modules/11.0/auditlog/): A third-party module that provided extra audit functionality for all models
- [Fontawesome5]: Provides access to fontawesome 5 icons


## Dependencies
- Odoo v11
- python 3
- pip3
- qrcode (The two factor authentication module depends on the python qrcode module. It can be installed by a simple pip3 install qrcode command)


## Installation
Detailed instructions for installing Odoo can be found [here](https://www.odoo.com/documentation/11.0/setup/install.html). Odoo comes in two versions: The community (free) version and the Enterprise version. The community version and the enterprise version share virtually the same codebase. The enterprise version however has a few additional modules that only paying customers can have access to. The eha clinic deployment runs on the enterprise version. The deployment steps are:
- Download and install odoo v11
- Request access to the [Odoo github repo](https://github.com/odoo/odoo) and download the v11 enterprise modules.
- Add path to the enterprise modules to the Odoo addons path
- Restart the Odoo server for enterprise modules to be loaded.
For the eHA clinic deployment, the following additional steps have to be done:
- Clone the [clinic repository](https://github.com/eHealthAfrica/eha-clinic)
- Add path to the clinic repository to the Odoo addons path (The top level folder eha_clinic should be added to the addons path)
- Restart the odoo server to load the additional modules from the eha clinic repository
- Install the partner firstname module
- Install the partner second lastname module
- Install the fontawesome5 module
- Install the oehealth module
