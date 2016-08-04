from collections import OrderedDict

OPENSTACK_CODENAMES = OrderedDict([
    ('2011.2', 'diablo'),
    ('2012.1', 'essex'),
    ('2012.2', 'folsom'),
    ('2013.1', 'grizzly'),
    ('2013.2', 'havana'),
    ('2014.1', 'icehouse'),
    ('2014.2', 'juno'),
    ('2015.1', 'kilo'),
    ('2015.2', 'liberty'),
    ('2016.1', 'mitaka'),
])

UBUNTU_OPENSTACK_RELEASE = OrderedDict([
    ('oneiric', 'diablo'),
    ('precise', 'essex'),
    ('quantal', 'folsom'),
    ('raring', 'grizzly'),
    ('saucy', 'havana'),
    ('trusty', 'icehouse'),
    ('utopic', 'juno'),
    ('vivid', 'kilo'),
    ('wily', 'liberty'),
    ('xenial', 'mitaka'),
])


OPENSTACK_CODENAMES = OrderedDict([
    ('2011.2', 'diablo'),
    ('2012.1', 'essex'),
    ('2012.2', 'folsom'),
    ('2013.1', 'grizzly'),
    ('2013.2', 'havana'),
    ('2014.1', 'icehouse'),
    ('2014.2', 'juno'),
    ('2015.1', 'kilo'),
    ('2015.2', 'liberty'),
    ('2016.1', 'mitaka'),
])

# The ugly duckling - must list releases oldest to newest
SWIFT_CODENAMES = OrderedDict([
    ('diablo',
        ['1.4.3']),
    ('essex',
        ['1.4.8']),
    ('folsom',
        ['1.7.4']),
    ('grizzly',
        ['1.7.6', '1.7.7', '1.8.0']),
    ('havana',
        ['1.9.0', '1.9.1', '1.10.0']),
    ('icehouse',
        ['1.11.0', '1.12.0', '1.13.0', '1.13.1']),
    ('juno',
        ['2.0.0', '2.1.0', '2.2.0']),
    ('kilo',
        ['2.2.1', '2.2.2']),
    ('liberty',
        ['2.3.0', '2.4.0', '2.5.0']),
    ('mitaka',
        ['2.5.0']),
])

# >= Liberty version->codename mapping
PACKAGE_CODENAMES = {
    'nova-common': OrderedDict([
        ('12.0', 'liberty'),
        ('13.0', 'mitaka'),
    ]),
    'neutron-common': OrderedDict([
        ('7.0', 'liberty'),
        ('8.0', 'mitaka'),
    ]),
    'cinder-common': OrderedDict([
        ('7.0', 'liberty'),
        ('8.0', 'mitaka'),
    ]),
    'keystone': OrderedDict([
        ('8.0', 'liberty'),
        ('9.0', 'mitaka'),
    ]),
    'horizon-common': OrderedDict([
        ('8.0', 'liberty'),
        ('9.0', 'mitaka'),
    ]),
    'ceilometer-common': OrderedDict([
        ('5.0', 'liberty'),
        ('6.0', 'mitaka'),
    ]),
    'heat-common': OrderedDict([
        ('5.0', 'liberty'),
        ('6.0', 'mitaka'),
    ]),
    'glance-common': OrderedDict([
        ('11.0', 'liberty'),
        ('12.0', 'mitaka'),
    ]),
    'openstack-dashboard': OrderedDict([
        ('8.0', 'liberty'),
        ('9.0', 'mitaka'),
    ]),
}
