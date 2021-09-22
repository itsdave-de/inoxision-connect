import frappe
from frappe.utils.pdf import get_pdf
from frappe.desk.form.load import get_attachments
import io
import requests
import ftplib
import urllib.parse


@frappe.whitelist()
def do_archive(doctype, name):
    settings = frappe.get_single("Inoxision Connect Settings")
    if settings.archive_enabled != 1:
        return False

    http_base = settings.http_endpoint
    language = frappe.get_single("System Settings")

    html = frappe.get_print(doctype, name, None, None, no_letterhead="no_letterhead")
    filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    f = io.BytesIO(get_pdf(html))

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
        file.close()                                    # close file and FTP

    session.quit()
