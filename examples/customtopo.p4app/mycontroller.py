from appcontroller import AppController

class CustomAppController(AppController):

    def __init__(self, *args, **kwargs):
        AppController.__init__(self, *args, **kwargs)

    def start(self):
        print "Calling the default controller to populate table entries"
        AppController.start(self)

    def stop(self):
        print "Mininet is about to stop"
        AppController.stop(self)

