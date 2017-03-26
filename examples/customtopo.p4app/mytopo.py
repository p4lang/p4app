from apptopo import AppTopo

class CustomAppTopo(AppTopo):

    def __init__(self, *args, **kwargs):
        # Initialize the top topo
        AppTopo.__init__(self, *args, **kwargs)

        print self.links()


