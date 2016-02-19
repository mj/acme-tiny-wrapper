# acme-tiny-wrapper

This is a small wrapper around the excellent acme-tiny for renewing Let's Encrypt SSL certificates.

## Configuration

`acme-tiny-wrapper` comes with sane defaults for most settings but you will most likely
have to adjust the locations of `acme-tiny` and your certificates. You can overwrite
all defaults settings in a INI file:

    [main]
    acmedir = /opt/diafygi/acme-tiny/
    challengedir = /srv/www/.challenges
    ...

## Renewal

acme-tiny will only renew certificates that expire soon because Let's Encrypt employs
restriction for how often a domain can request a new certificate. The config setting
`renewal-threshold` is the number of days that controls this threshold.

### Crontab usage

It is recommended to run the renewal once a day for each domain that.

    5 11    * * *   certs   python /path/to/main.py --config /path/to/config.ini renew martinjansen.com
