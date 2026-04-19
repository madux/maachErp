#FROM odoo:12.0
FROM odoo@sha256:4f2cd56b55e3563da358218bcfeb4126236e5b619514082c478a0997c93d8b04
LABEL maintainer="devops@ehealthafrica.org"

USER root

ADD config/requirements.txt /tmp/requirements.txt
RUN apt update -qq && apt install -qq --yes python3-pip && pip3 install --upgrade pip && pip3 install -r /tmp/requirements.txt
RUN apt-get -y update && apt-get install -y gettext python-pip git supervisor

RUN pip install awscli psycogreen phonenumbers raven

COPY ./config/entrypoint.sh /odoo-entrypoint.sh
COPY ./config/supervisor.conf /etc/supervisor/conf.d/odoo.conf
RUN chmod +x /odoo-entrypoint.sh

COPY ./config/odoo.conf.tpl /etc/odoo/odoo.conf.tpl

# Copy modules
COPY build/eha_clinic /mnt/eha-addons/eha_clinic
COPY build/enterprise /mnt/eha-addons/enterprise

# remove other files
RUN cd /mnt/eha-addons/eha_clinic && rm -rf core-app terraform docker-compose.yml .travis.yml

ENTRYPOINT ["/odoo-entrypoint.sh"]
