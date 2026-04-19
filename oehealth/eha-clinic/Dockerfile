FROM odoo:13.0
#FROM odoo@sha256:4f2cd56b55e3563da358218bcfeb4126236e5b619514082c478a0997c93d8b04
LABEL maintainer="devops@ehealthafrica.org"

USER root

ENV DB_CONN=64
ENV USER=ehaclinicv13
ENV WORKERS_NUMBER=240
ENV LIMIT_MEMORY_HARD=2684354560
ENV LIMIT_MEMORY_SOFT=2147483648
ENV LIMIT_CPU=3600
ENV LIMIT_CPU_REAL=3600
ENV LOG_LEVEL=warn
ENV LOG_HANDLER=":WARN"
ENV MAX_CRON_THREADS=1
ENV SENTRY_ENABLED=True

ARG HOST
ARG SENTRY_DSN
ARG ADMIN_PASSWORD
ARG database_password

ENV HOST=$HOST
ENV SENTRY_DSN=$SENTRY_DSN
ENV ADMIN_PASSWORD=$ADMIN_PASSWORD
ENV PASSWORD=$database_password

ADD core-app/config/requirements.txt /tmp/requirements.txt
RUN apt update -qq && apt install -qq --yes python3-pip && pip3 install --upgrade pip && pip3 install -r /tmp/requirements.txt
RUN apt-get -y update && apt-get install -y gettext python-pip git supervisor

RUN pip install awscli psycogreen phonenumbers raven

COPY core-app/config/entrypoint.sh /odoo-entrypoint.sh
RUN chmod +x /odoo-entrypoint.sh

COPY core-app/config/odoo.conf.tpl /etc/odoo/odoo.conf.tpl
COPY core-app/config/supervisor.conf /etc/supervisor/conf.d/odoo.conf
COPY core-app/config/odoo-newrelic.ini /etc/odoo-newrelic.ini

# include commit hash
#COPY ./.git/ref /var/run/clinics/REVISION

#install git
RUN apt-get update && apt-get install git

# Copy modules

COPY ./ /mnt/eha-addons/eha-clinic/
RUN cd /mnt/eha-addons/

ARG GIT_ENT_URL

# get enterprise modules
RUN git clone --branch 13.0 $GIT_ENT_URL /mnt/eha-addons/enterprise


# remove other files
RUN cd /mnt/eha-addons/eha-clinic && rm -rf core-app terraform docker-compose.yml .travis.yml

ENTRYPOINT ["/odoo-entrypoint.sh","start"]