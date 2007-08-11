

import uno
import string
import unohelper
import xmlrpclib
import base64, tempfile

from com.sun.star.task import XJobExecutor
import os
import sys
if __name__<>'package':
    from lib.gui import *
    from lib.error import *
    from LoginTest import *

#

class ModifyExistingReport(unohelper.Base, XJobExecutor):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "tiny_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
#        elif __name__<>"package":
#            self.database="trunk_1"
        self.win=DBModalDialog(60, 50, 180, 120, "Modify Existing Report")
        self.win.addFixedText("lblReport", 2, 3, 60, 15, "Report Selection")
        self.win.addComboListBox("lstReport", -1,15,178,80 , False,itemListenerProc=self.lstbox_selected)
        self.lstReport = self.win.getControl( "lstReport" )
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        sock = xmlrpclib.ServerProxy(docinfo.getUserFieldValue(0) +'/xmlrpc/object')
        self.ids = sock.execute(database, 3, docinfo.getUserFieldValue(1), 'ir.actions.report.xml' ,  'search', [('report_sxw_content','<>',False)])
        #res_sxw = sock.execute(docinfo.getUserFieldValue(2), 3, docinfo.getUserFieldValue(1), 'ir.actions.report.xml', 'report_get', ids[0])
        fields=['name','report_name','model']
        self.res_other = sock.execute(database, 3, docinfo.getUserFieldValue(1), 'ir.actions.report.xml', 'read', self.ids,fields)
        for i in range(self.res_other.__len__()):
            if self.res_other[i]['name']<>"":
                self.lstReport.addItem(self.res_other[i]['name'],self.lstReport.getItemCount())

        #self.win.addFixedText("lblModuleSelection1", 2, 98, 178, 15, "Module Selection")
        self.win.addButton('btnSave',-2 ,-5,80,15,'Save to Temp Directory'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )
        self.win.addButton('btnCancel',-2 -80 ,-5,45,15,'Cancel'
                      ,actionListenerProc = self.btnOkOrCancel_clicked )
        #os.system( "oowriter /home/hjo/Desktop/aaa.sxw &" )
        self.win.doModalDialog("lstReport",self.res_other[0]['name'])

    def lstbox_selected(self,oItemEvent):
        pass
        #print self.win.getListBoxSelectedItemPos("lstReport")
        #self.win.setEditText("lblModuleSelection1",tempfile.mktemp('.'+"sxw"))
    def btnOkOrCancel_clicked(self, oActionEvent):
        if oActionEvent.Source.getModel().Name == "btnSave":
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            sock = xmlrpclib.ServerProxy(docinfo.getUserFieldValue(0) +'/xmlrpc/object')
            res = sock.execute(database, 3, docinfo.getUserFieldValue(1), 'ir.actions.report.xml', 'report_get', self.ids[self.win.getListBoxSelectedItemPos("lstReport")])
            fp_name = tempfile.mktemp('.'+"sxw")
            if res['report_sxw_content']:
                data = base64.decodestring(res['report_sxw_content'])

                fp = file(fp_name, 'wb')
                fp.write(data)
                fp.close()
            url="file://"+fp_name
            arr=Array()
            oDoc2 = desktop.loadComponentFromURL(url, "tiny", 55, arr)
            #oVC= oDoc2.getCurrentController().getViewCursor()
            #oText = oVC.getText()
            #oCur=oText.createTextCursorByRange(oVC.getStart())
            #oCur.insertDocumentFromURL(url, Array())
            docinfo2=oDoc2.getDocumentInfo()
            docinfo2.setUserFieldValue(2,self.ids[self.win.getListBoxSelectedItemPos("lstReport")])
            docinfo2.setUserFieldValue(1,docinfo.getUserFieldValue(1))
            docinfo2.setUserFieldValue(0,docinfo.getUserFieldValue(0))
            docinfo2.setUserFieldValue(3,self.res_other[self.win.getListBoxSelectedItemPos("lstReport")]['model'])
            print "abc"
            if oDoc2.isModified():
                print "abc"
                if oDoc2.hasLocation() and not oDoc2.isReadonly():
                    print "abc"
                    oDoc2.store()
            print "abc"
                #End If
            #End If
            #os.system( "`which ooffice` '-accept=socket,host=localhost,port=2002;urp;'")
            ErrorDialog("Download is Completed","Your file has been placed here :\n"+ fp_name,"Download Message")
            print "abc"
            self.win.endExecute()
        elif oActionEvent.Source.getModel().Name == "btnCancel":
            self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    ModifyExistingReport(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( \
            ModifyExistingReport,
            "org.openoffice.tiny.report.modifyreport",
            ("com.sun.star.task.Job",),)

