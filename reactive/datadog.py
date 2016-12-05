
import yaml

from charms.reactive import (
     when,
     when_not,
     set_state,
     remove_state,
     RelationBase,
)

from charmhelpers.core.host import service_restart
from charmhelpers.core.hookenv import (
    config,
    metadata,
)

from charmhelpers.core.templating import render
from charms import apt


DATADOG_CONFD = '/etc/dd-agent/conf.d'


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


@when('config.changed.api-key')
def reset_cfg():
    remove_state('datadog.configured')


@when('datadog.configured')
def configure_integrations():
    """Configure all connected integrations currently available"""
    # Use the metadata charm helper to load the metadata.yaml for datadog
    # charm dynamically and parse requires relations
    integrations = metadata().get('requires').keys()

    # Loop over all the integrations defined in the charms metadata and
    # check if they're available (ready to be configured)
    for integration in integrations:
        new_integration = False
        example_file = os.path.join(DATADOG_CONFD,
                                    '{}.yaml.example'.format(integration))

        # Make sure this integration exists and the relation is available
        if not os.path.exists(example_file):
            continue

        if not is_state('{}.available'.format(integration)):
            continue

        # Load up the interfaces from reactive, extract the goodies and write
        # out configuration files
        rel = RelationBase.from_state(integration)
        config = rel.configuration()

        # Okay, we have configuration data, lets write out the file
        integration_cfg = os.path.join(DATADOG_CONFD, '{}.yaml'.format(integration))
        integration_file = integration_cfg

        # This is the first time we've written this configuration file
        # Load from the .example file for defaults, force restart
        if not os.path.exists(integration_file):
            integration_file = example_file
            new_integration = True

        # Load existing datadog configuration
        with open(integration_file) as f:
            cfg_file = yaml.safe_load(f.read())

        inst = cfg_file.get('instances', [])
        if inst[0] == config and not new_integration:
            continue  # No changes to configuration, and not a new integration

        cfg_file['instances'][0] = config

        # Write configuration file
        with open(integration_cfg, 'w') as f:
            f.write(yaml.safe_dump(cfg_file, default_flow_style=False))

        restart = True

    if restart:
        service_restart('dd-agent')
