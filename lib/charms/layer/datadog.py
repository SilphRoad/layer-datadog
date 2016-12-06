
import os
import yaml

from charmhelpers.core.hookenv import status_set


confd = '/etc/dd-agent/conf.d'


def configure_integration(name, data):
    example_file = os.path.join(confd, '{}.yaml.example'.format(name))

    integration_cfg = os.path.join(confd, '{}.yaml'.format(name))
    integration_file = integration_cfg

    # Make sure this integration exists and the relation is available
    if not os.path.exists(example_file):
        return

    # This is the first time we've written this configuration file
    # Load from the .example file for defaults, force restart
    if not os.path.exists(integration_file):
        integration_file = example_file
        new_integration = True

    # Load existing datadog configuration
    with open(integration_file) as f:
        cfg_file = yaml.safe_load(f.read())

    inst = cfg_file.get('instances', [])
    if inst[0] == data and not new_integration:
        return

    status_set('maintenance', 'configuring {} integration'.format(name))

    cfg_file['instances'][0] = data

    # Write configuration file
    with open(integration_cfg, 'w') as f:
        f.write(yaml.safe_dump(cfg_file, default_flow_style=False))
