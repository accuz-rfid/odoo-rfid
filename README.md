# Odoo InvenTrack™ RFID WMS

The best RFID integration for Android devices, designed for seamless WMS operations.

## Deployment Guide

Follow these steps to deploy the module on your Odoo server:

### 1. Download & Prepare
* Clone or download the repository to your local machine.
* Transfer the `rfid_wms` folder to your Odoo server (e.g., under `/home/odoo_app/accuz_demo/odoo-rfid/`).

### 2. Configure Addons Path
* Open your Odoo configuration file (e.g., `odoo.conf`).
* Add the parent directory of the module to the `addons_path`:
  ```text
  addons_path = /your/existing/paths, /home/odoo_app/accuz_demo/odoo-rfid

* Note: Ensure the path points to the directory containing the rfid_wms folder.

### 3. Restart Odoo server to apply the changes

### 4. Install module in Odoo
* Activate Developer Mode in Odoo Settings, Update Apps List and confirm the update;
* Remove the default "apps" filter in the search bar;
* Search for rfid_wms and activate.