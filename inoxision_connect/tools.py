from os import set_inheritable
import frappe
from frappe.utils.pdf import get_pdf
from frappe.desk.form.load import get_attachments
import io
import requests
import ftplib
import urllib.parse
from wand.image import Image
 
#ny = Image(filename ='pdf new york.pdf')
#ny_converted = ny.convert('jpg')
#for img in ny_converted.sequence:
#  page = ny(image = img)
#  page.save(filename='new york pdf to image.jpg')


@frappe.whitelist()
def archive_to_inoxision(doc, method=None):
    settings = frappe.get_single("Inoxision Connect Settings")
    if not settings.archive_enabled == 1:
        return None
    active_doctypes = frappe.get_all("Inoxision Connect Settings Active Doctype", fields="doctype_link", as_list=True)
    if (doc.doctype,) not in active_doctypes:
        return None
    do_archive(doc.doctype, doc.name)


@frappe.whitelist()
def do_archive(doctype, name):
    settings = frappe.get_single("Inoxision Connect Settings")
    if settings.inputpath == "" or settings.outputarchivename == "":
        frappe.msgprint("Keine Archivierung möglich. Inoxision Connect Settings unvollständig.")
        return False

    language = frappe.get_single("System Settings")

    html = frappe.get_print(doctype, name, None, None, no_letterhead="no_letterhead")
    filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    f_pdf = io.BytesIO(get_pdf(html))
    session = ftplib.FTP(settings.server, settings.user, settings.password)


    if settings.convert_to_tiff == 1:
        converted_return = convert_to_tif(f_pdf, filename, settings)
        f = converted_return[0]
        filename = converted_return[1]

    if settings.path:
        if settings.path >= "/":
            session.cwd(settings.path)
    session.storbinary("STOR " + filename , f)
    control_file = get_inoxision_control_file_content(doctype, name, filename, settings)
    session.storbinary("STOR " + filename + ".txt", control_file)

    f = None
    control_file = None

    attachments = get_attachments(doctype, name)
    for a in attachments:
        f = frappe.utils.get_bench_path() + "/sites" + frappe.utils.get_site_path()[1:] + a.file_url
        file = open(f, "rb") 
        session.storbinary("STOR " + a.file_name, file)     # send the file
        print(a.filename)
        control_file = get_inoxision_control_file_content(doctype, name, a.filename, settings)
        session.storbinary("STOR " + a.file_name + ".txt", file)

        file.close()
    
    session.quit()
    

def get_inoxision_control_file_content(doctype, name, filename, settings):
    control_file_content = ""
    kopf_zeile = "[Execute]\nInputType=IMAGE\nInputPath=" + str(settings.inputpath)+"\nInputPattern=" + str(filename) + "\nAutoExecute=" + str(settings.autoexecute)+"\nOutputArchiveName=" + str(settings.outputarchivename) +"\n"
    schluss_zeile = "\nSwapProcess=1\nCreateFullTextChecked=1\nDeleteConfigFile=1"                                    

    keyword_list = frappe.get_all("Inoxision Connect Settings Field Assignment",filters = {"doctype_link":doctype},fields= ["destination_field","source_field"])
    doctype_doc = frappe.get_doc(doctype,name)
    keyword_zeile = "KeywordValues="
    for keyword in keyword_list:
        a = str(getattr(doctype_doc, keyword["source_field"]))
        if a !="":
            keyword_zeile += "Belege." + keyword["destination_field"] + "|" + a +"|"
        else:
            continue

    control_file_content = kopf_zeile + keyword_zeile + schluss_zeile
    bytes_io = io.BytesIO(control_file_content.encode())
    return bytes_io
    
def convert_to_tif(input_file, filename, settings):
    if settings.resolution > 0:
        resolution = settings.resolution
    else:
        resolution = 200
    output_file = io.BytesIO()
    filename = filename.replace(".pdf",".tif")
    with Image(file=input_file, resolution=resolution) as original:
        with original.convert("tif") as converted:
            converted.save(file=output_file)
    output_file.seek(0)
    return (output_file, filename)