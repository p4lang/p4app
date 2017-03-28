from apptopo import AppTopo

class CustomAppTopo(AppTopo):

    def __init__(self, *args, **kwargs):
        # Initialize the top topo
        AppTopo.__init__(self, *args, **kwargs)

        manifest, target = kwargs['manifest'], kwargs['target']

        print "Using target:", manifest['targets'][target]

        # Update a link's latency
        for link in self.iterLinks(withInfo=True):
            n1, n2, info = link
            if n1 == 's1' and n2 == 's2':
                info['delay'] = '123ms'

        print self.links(withInfo=True)

