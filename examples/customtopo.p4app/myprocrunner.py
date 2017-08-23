from appprocrunner import AppProcRunner, AppProcess

class CustomAppProccess(AppProcess):
    def __init__(self, *args, **kwargs):
        AppProcess.__init__(self, *args, **kwargs)

    def formatCmd(self, raw_cmd):
        print "cmd before formatting:", raw_cmd
        cmd = AppProcess.formatCmd(self, raw_cmd)
        print "cmd after formatting:", cmd
        return cmd

class CustomAppProcRunner(AppProcRunner):

    def __init__(self, *args, **kwargs):
        AppProcRunner.__init__(self, *args, **kwargs)
        self.AppProcessClass = CustomAppProccess
