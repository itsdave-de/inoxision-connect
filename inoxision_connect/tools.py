from os import set_inheritable
import frappe
from frappe.utils.pdf import get_pdf
from frappe.desk.form.load import get_attachments
import io
import requests
import ftplib
import urllib.parse


@frappe.whitelist()
def archive_to_inoxision(doc, method=None):
    settings = frappe.get_single("Inoxision Connect Settings")
    if not settings.archive_enabled == 1:
        return None
    active_doctypes = frappe.get_all("Inoxision Connect Settings Active Doctype", fields="doctype_link", as_list=True)
    if (doc.doctype,) not in active_doctypes:
        return None

    do_archive(doc.doctype, doc.name)
    print(doc.doctype)
    print(doc.name)

@frappe.whitelist()
def do_archive(doctype, name):
    settings = frappe.get_single("Inoxision Connect Settings")
    if settings.archive_enabled != 1:
        return False
    if settings.inputpath == "" or settings.inputpattern == "" or settings.outputarchivename == "":
        frappe.msgprint("Keine Archivierung möglich. Inoxision Connect Settings unvollständig.")
        return False
        
    http_base = settings.http_endpoint
    language = frappe.get_single("System Settings")

    html = frappe.get_print(doctype, name, None, None, no_letterhead="no_letterhead")
    filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    #f = io.BytesIO(get_pdf(html))
    f = io.BytesIO(b"")
    session = ftplib.FTP(settings.server, settings.user, settings.password)

    if settings.path:
        if settings.path >= "/":
            session.cwd(settings.path)
    session.storbinary("STOR " + filename , f)

    f = None

    attachments = get_attachments(doctype, name)
    for a in attachments:
        # In [2]: do_archive("Sales Invoice", "SINV-250014")
        #[{'name': 'b9dee55174', 'file_name': 'datasheet.pdf', 'file_url': '/private/files/datasheet.pdf', 'is_private': 1}]

        #In [3]: frappe.utils.get_bench_path()
        #Out[3]: '/Users/dave/frappe-bench13'

        #In [4]: frappe.utils.get_site_path()
        #Out[4]: './dev12.erpnext.itsdave.de'
        f = frappe.utils.get_bench_path() + "/sites" + frappe.utils.get_site_path()[1:] + a.file_url
        file = open(f, "rb") 
        session.storbinary("STOR " + a.file_name, file)     # send the file
        file.close()
    kopf_zeile = "[Execute]\nInputType=IMAGE\nInputPath=" + str(settings.inputpath)+"\nInputPattern=" + str(settings.inputpattern) + "\nAutoExecute=" + str(settings.autoexecute)+"\nOutputArchiveName=" + str(settings.outputarchivename) +"\n"
    schluss_zeile = "\nSwapProcess=1\nCreateFullTextChecked=1\nDeleteConfigFile=1"                                    
    mitte = get_keyword(doctype,name)
    textfile = kopf_zeile + mitte + schluss_zeile
    print(textfile)
    session.quit()
    
def get_keyword(doctype, name):
    
    keyword_list = frappe.get_all("Inoxision Connect Settings Field Assignment",filters = {"doctype_link":doctype},fields= ["destination_field","source_field"])
    doctype_doc = frappe.get_doc(doctype,name)
    keyword_zeile = "KeywordValues="
    for keyword in keyword_list:
        a = str(getattr(doctype_doc, keyword["source_field"]))
        if a !="":
            keyword_zeile += "Belege." + keyword["destination_field"] + "|" + a +"|"
        else:
            continue
    return keyword_zeile
    
    
    
        
    #print(keyword_list)
    # SwapProcess=1
    # CreateFullTextChecked=1
    # DeleteConfigFile=1