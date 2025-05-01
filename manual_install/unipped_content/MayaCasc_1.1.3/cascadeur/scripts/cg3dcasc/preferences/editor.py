import os
import cg3dguru.ui
import cg3dcasc.preferences

class Cg3dCascPrefs(cg3dguru.ui.Window):
    def __init__(self): 
        uiFilepath = os.path.join(cg3dcasc.preferences.__path__[0], 'preferences.ui')
        super(Cg3dCascPrefs, self).__init__('cg3dcasc_prefs', uiFilepath) #, custom_widgets = custom_widgets)

        self.prefs = None
        self.init_ui()
        self.ui.apply.pressed.connect(self.save_prefs)
        self.ui.cancel.pressed.connect(self.cancel)


    def init_ui(self, prefs=None):
        if prefs is None:
            prefs = cg3dcasc.preferences.get()
            
        self.prefs = prefs

        idx = self.ui.bake_choice.findText(prefs.bake_animations.value)
        self.ui.bake_choice.setCurrentIndex(idx)

        
    def save_prefs(self, *args, **kwargs):
        self.prefs.bake_animations = cg3dcasc.preferences.OptionEnum(self.ui.bake_choice.currentText())
        cg3dcasc.preferences.set(self.prefs)
        self.ui.close()


    def cancel(self, *args, **kwargs):
        self.ui.close()



def run(*args):
    editor = Cg3dCascPrefs()
    editor.ui.resize(editor.ui.layout().minimumSize())
    editor.ui.show()