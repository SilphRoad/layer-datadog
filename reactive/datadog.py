
from charms import apt
from charms.layer import datadog

from charms.reactive import (
    when,
    when_not,
    set_state,
    remove_state,
    RelationBase,
)

from charmhelpers.core.host import service_restart
from charmhelpers.core.templating import render

from charmhelpers.core.hookenv import (
    config,
    metadata,
    status_set,
    log,
)


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

    service_restart('datadog-agent')
    set_state('datadog.configured')


@when('config.default.api-key')
def not_ready():
    status_set('blocked', 'need a valid api-key')


@when('config.changed.api-key')
def reset_cfg():
    remove_state('datadog.configured')


@when('datadog.configured')
def configure_integrations():
    """Configure all connected stats integrations currently available"""
    # Use the metadata charm helper to load the metadata.yaml for datadog
    # charm dynamically and parse requires relations
    integrations = metadata().get('requires').keys()
    restart = False

    # Loop over all the integrations defined in the charms metadata and
    # check if they're available (ready to be configured)
    log('Processing the following integrations: {}'.format(','.join(integrations))
    for integration in integrations:
        log('Processing {} integration'.format(integration))
        safe_name = integration.replace('-', '_')

        # Load up the interfaces from reactive, extract the goodies and write
        # out configuration files
        rel = RelationBase.from_state('{}.available'.format(integration))

        if not rel:
            continue

        if not hasattr(rel, 'configuration'):
            continue

        datadog.configure_integration(safe_name, rel.configuration())

        restart = True

    if restart:
        service_restart('dd-agent')

    status_set('active', 'ready')
