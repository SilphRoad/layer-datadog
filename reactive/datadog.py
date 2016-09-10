
import yaml

from charms.reactive import (
     when,
     when_not,
     set_state,
     remove_state,
)

from charmhelpers.core.host import service_restart
from charmhelpers.core.templating import render

from charm import apt


@when_not('apt.installed.datadog-agent')
def install_datadog():
    apt.queue_install('datadog-agent')


@when('apt.installed.datadog-agent')
@when_not('datadog.configured')
@when_not('config.default.api-key')
def configure():
    render(
        source='datadog.conf.j2',
        target='/etc/dd-agent/datadog.conf',
        context={
            'api_key': config().get('api-key'),
        }
    )

    service_restart('dd-agent')
    set_state('datadog.configured')


@when('config.changed.api-key')
def reset_cfg():
    remove_state('datadog.configured')


@when('php-fpm.available')
@when('apt.installed.datadog-agent')
@when_not('datadog.php-fpm.configured')
def configure_php_fpm(php_fpm):
    with open('/etc/dd-agent/conf.d/php_fpm.yaml.example') as f:
        conf = yaml.safe_load(f.read())

    inst = conf.get('instances', [])
    inst[0] = {
        'ping_url': php_fpm.ping_url,
        'ping_reply': php_fpm.ping_reply,
        'status_url': php_fpm.status_url,
    }

    conf['instances'] = inst

    with open('/etc/dd-agent/conf.d/php_fpm.yaml', 'w') as f:
        f.write(yaml.dump(conf, default_flow_style=False))

    service_restart('dd-agent')
    set_state('datadog.php-fpm.configured')
