# -*- coding: UTF-8 -*-
# Copyright 2021 Alberto Buffolino, released under GPLv2

import appModuleHandler
import controlTypes as ct
import winUser
from NVDAObjects.IAccessible import IAccessible, MenuItem
from keyboardHandler import KeyboardInputGesture as InputGesture

# for pre-2022.1 compatibility
if hasattr(ct, 'Role'):
	roles = ct.Role
else:
	roles = type('Enum', (), dict([(x.split("ROLE_")[1], getattr(ct, x)) for x in dir(ct) if x.startswith("ROLE_")]))

"""Useful links:
- Combobox messages and their meaning:
https://docs.microsoft.com/en-us/windows/win32/controls/bumper-combobox-control-reference-messages
- Combobox message values:
https://www.pinvoke.net/default.aspx/Constants/CB_.html
- Some examples:
https://bytes.com/topic/c-sharp/answers/537006-drop-down-combobox-programatically
https://pastebin.com/raw/hQY4n400
"""

# combobox constants
CB_SHOWDROPDOWN = 0x14F
CB_GETCOUNT = 0x0146
CB_GETCURSEL = 0x0147
CB_SETCURSEL = 0x014E
CB_GETDROPPEDSTATE = 0x0157
CB_ERR = -1


class AppModule(appModuleHandler.AppModule):

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.role == roles.COMBOBOX:
			clsList.insert(0, ACLogCombobox)
		elif obj.role == roles.EDITABLETEXT and obj.simpleParent.role == roles.COMBOBOX:
			clsList.insert(0, ACLogEditCombobox)
		elif obj.role == roles.STATICTEXT:
			clsList.insert(0, ACLogStaticText)
		elif obj.role == roles.MENUITEM:
			clsList.insert(0, ACLogMenuItem)


class ACLogCombobox(IAccessible):

	def isExpanded(self):
		res = winUser.sendMessage(self.windowHandle, CB_GETDROPPEDSTATE, 0, 0)
		return bool(res)

	def expand(self):
		res = winUser.sendMessage(self.windowHandle, CB_SHOWDROPDOWN, 1, 0)
		return bool(res)

	def getItemCount(self):
		res = winUser.sendMessage(self.windowHandle, CB_GETCOUNT, 0, 0)
		return res

	def getSelection(self):
		res = winUser.sendMessage(self.windowHandle, CB_GETCURSEL, 0, 0)
		return res

	def setSelection(self, index):
		res = winUser.sendMessage(self.windowHandle, CB_SETCURSEL, index, 0)
		return res

	def scroll(self, direction):
		newSel = None
		# if edit contains partial value before expanding,
		# selection will be different before and after
		# but expanding sets by itself the correct selection for autofill
		curSel1 = self.getSelection()
		if not self.isExpanded():
			self.expand()
		curSel2 = self.getSelection()
		if curSel1 == curSel2:
			# scroll from a value previously set
			newSel = self.setSelection(curSel2-1 if direction=="up" else curSel2+1)
		elif (curSel1,curSel2) == (0,-1):
			# scroll from empty value
			newSel = self.setSelection(1 if direction=="down" else self.getItemCount()-1)
		if newSel == CB_ERR:
			# circular scrolling from first/last position
			self.setSelection(0 if direction=="down" else self.getItemCount()-1)

	def script_scroll(self, gesture):
		key = gesture.mainKeyName
		if key in ("upArrow", "downArrow"):
			self.scroll(key.strip("Arrow"))


class ACLogEditCombobox(IAccessible):

	def script_caret_moveByLine(self, gesture):
		self.simpleParent.script_scroll(gesture)
		# avoid "selected" announcement
		self.terminateAutoSelectDetection()
		super(ACLogEditCombobox, self).script_caret_moveByLine(gesture)


class ACLogStaticText(IAccessible):

	def event_nameChange(self):
		# UTC and time windows silently update
		# their staticText every second,
		# so suppress this useless event
		pass


class ACLogMenuItem(MenuItem):

	def initOverlayClass(self):
		for arrow in ("upArrow", "downArrow"):
			self.bindGesture("kb:%s"%arrow, "exploreMenu")
		self.bindGesture("kb:escape", "closeMenu")

	def script_exploreMenu(self, gesture):
		if not self.childCount and self.parent.role == roles.MENUBAR:
			# avoid to focus out of menu
			return
		gesture.send()

	def script_closeMenu(self, gesture):
		gesture.send()
		if self.parent.role != roles.MENUBAR:
			# esc on internal menuitems not hides menubar, so...
			InputGesture.fromName("alt").send()

