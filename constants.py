import wx
import wx.lib.newevent

def error(msg):
    dlg = wx.MessageDialog(None, msg, "Unexpected Error", wx.OK|wx.ICON_ERROR)
    dlg.ShowModal() # Shows it
    dlg.Destroy() # finally destroy it when finished.

def crash(msg):
    error(msg)
    sys.exit(msg)

class DType:
    COMPLEX = "CPLX"
    STRING = "str"
    INTEGER = "int"
    BOOLEAN = "bool"

#CXEItemChangedEvent, EVT_CXE_ITEM_CHANGED = wx.lib.newevent.NewCommandEvent()

myEVT_CXE_ITEM_CHANGED = wx.NewEventType()
EVT_CXE_ITEM_CHANGED = wx.PyEventBinder(myEVT_CXE_ITEM_CHANGED, 0)

class CXEItemChangedEvent(wx.PyEvent):
	def __init__(self, obj):
		wx.PyEvent.__init__(self, wx.ID_ANY, myEVT_CXE_ITEM_CHANGED)
		self.ResumePropagation(64)
		self.SetEventObject(obj)

CHANGED_COLOUR = wx.Colour(255,200,200)
SELECTED_COLOUR = wx.Colour(32, 32, 220)
CHANGED_SELECTED_COLOUR = wx.Colour(220, 32, 32)
