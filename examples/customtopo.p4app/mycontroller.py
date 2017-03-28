from appcontroller import AppController

class CustomAppController(AppController):

    def __init__(self, *args, **kwargs):
        AppController.__init__(self, *args, **kwargs)

    def start(self):
        print "Calling the default controller to populate table entries"
        AppController.start(self)

    def stop(self):
        reg_val = self.read_register('forward_count_register', 0)
        print "The switch forwarded a total of %d packets" % reg_val
        AppController.stop(self)

