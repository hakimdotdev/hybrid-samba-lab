import os
import subprocess
import tkinter as tk
from tkinter import ttk
import ttkthemes
from ttkthemes import ThemedTk

import getpass

class IPConfigWindow(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        #Statusbar

        statusbar = tk.Label(self, text="Ready to take off..", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        statusbar.pack()
        # Create a LabelFrame widget for the "Network" group
        network_frame = ttk.LabelFrame(self, text="Network")
        network_frame.pack(fill="both", expand=True)

        # Create the "DNS-Server" label as a child of the network_frame widget
        ttk.Label(network_frame, text="DNS-Server:").pack()
        self.dnssrv_enty = ttk.Entry(network_frame)
        self.dnssrv_enty.pack()

        # Create the "IP-Addresse" label as a child of the network_frame widget
        ttk.Label(network_frame, text="IP-Addresse:").pack()
        self.ip_entry = ttk.Entry(network_frame)
        self.ip_entry.pack()

        # Create the "Subnetzmaske" label as a child of the network_frame widget
        ttk.Label(network_frame, text="Subnetz CIDR (/24):").pack()
        self.subnet_entry = ttk.Entry(network_frame)
        self.subnet_entry.pack()

        # Create the "Gateway" label as a child of the network_frame widget
        ttk.Label(network_frame, text="Gateway:").pack()
        self.gateway_entry = ttk.Entry(network_frame)
        self.gateway_entry.pack()

        # Create a LabelFrame widget for the "Domain" group
        domain_frame = ttk.LabelFrame(self, text="Domain")
        domain_frame.pack(fill="both", expand=True)

        # Create the "Domain" label as a child of the domain_frame widget
        ttk.Label(domain_frame, text="Domain:").pack()
        self.domain_entry = ttk.Entry(domain_frame)
        self.domain_entry.pack()

        # Create the Checkbox for Sysvol
        self.sysvol_checkbox = ttk.Checkbutton(domain_frame, text="Prepare Sysvol Replication")
        self.sysvol_checkbox.pack()

        self.start_button = ttk.Button(self, text="Start", command=self.start).pack()

        self.quit_button = ttk.Button(self, text="Quit", command=self.destroy).pack()

    def start(self):
        try:
            ttk.statusbar.config(text="Checking input and preparing the installation..")
            # Attempt to retrieve the values from the entry widgets
            ipaddr = self.ip_entry.get()
            subnet = self.subnet_entry.get()
            gateway = self.gateway_entry.get()
            dnssrv = self.dnssrv_enty.get()
            domain = self.domain_entry.get()
        except AttributeError:
    # Handle the case where one or more of the entry widgets is not defined
            print("One or more entry widgets is not defined!")
        # Create the Netplan configuration
        netplan_config = f"""
        network:
          version: 2
          renderer: networkd
          ethernets:
            eth0:
              dhcp4: no
              addresses: [{ipaddr}/{subnet}]
              gateway4: {gateway}
              nameservers: {domain}
                addresses: [{dnssrv}]
        """

        # Write the configuration to the Netplan file
        with open("/etc/netplan/config.yaml", "w") as f:
          f.write(netplan_config)

        # Apply the configuration to the system
        try:
            subprocess.run(["netplan", "apply"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to apply the Netplan configuration.")
            exit(1)
        # Update the package manager
        try:
            subprocess.run(["apt-get", "update", "-y"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to update the package manager.")
            exit(1)
        # Upgrade installed packages
        try:
            subprocess.run(["apt-get", "upgrade", "-y"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to upgrade installed packages.")
            exit(1)

        # Move the krb5.conf file to a backup location
        try:
            subprocess.run(["mv", "/etc/krb5.conf", "/etc/krb5.conf.bak"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to move the krb5.conf file to a backup location.")
            exit(1)

        # Install necessary packages
        try:
            ttk.statusbar.config(text="Installing and Provisioning..")
            subprocess.run(["apt-get", "-y", "install", "samba", "heimdal-clients", "smbclient", "winbind", "ntp", "ldb-tools"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to install necessary packages.")
            exit(1)

        # Move existing configuration files to backup locations
        try:
            subprocess.run(["mv", "/etc/samba/smb.conf{,.bu.orig}"], check=True)
            subprocess.run(["mv", "/etc/krb5.conf{,.bu.orig}"], check=True)
            subprocess.run(["mv", "/etc/ntp.conf{,.bu.orig}"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to move existing configuration files to backup locations.")
            exit(1)

        # Remove existing databases
        try:
            subprocess.run(["rm", "-f", "/run/samba/*.tdb"], check=True)
            subprocess.run(["rm", "-f", "/var/lib/samba/*.tdb"], check=True)
            subprocess.run(["rm", "-f", "/var/cache/samba/*.tdb"], check=True)
            subprocess.run(["rm", "-f", "/var/lib/samba/private/*.tdb"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to remove existing databases.")
            exit(1)
        ###### TODO Provision Ausschließen String role und dns
        # Upgrade the server to a domain controller in non-interactive mode
        #try:
        #    subprocess.run(["samba-tool", "domain", "provision", "--use-rfc2307", "--non-interactive", "--realm="+realm, "--domain="+domain, "--server-role="DC", "--dns-backend="SAMBA_INTERNAL", "--adminpass="+password], check=True)
        #except subprocess.CalledProcessError:
        #    print("Failed to upgrade the server to a domain controller.")
        #    exit(1)

        # Copy the krb5.conf file from the Samba private directory to the /etc directory
        try:
            subprocess.run(["cp", "/var/lib/samba/private/krb5.conf", "/etc/"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to copy the krb5.conf file.")
            exit(1)

        # Unmask and enable the samba-ad-dc service
        try:
            subprocess.run(["systemctl", "unmask", "samba-ad-dc"], check=True)
            subprocess.run(["systemctl", "enable", "samba-ad-dc"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to enable the samba-ad-dc service.")
            exit(1)
        ttk.statusbar.config(text="Success!")
        print("Successfully upgraded the server to a domain controller.")

if __name__ == "__main__":
    window = ThemedTk(theme="adapta")
    window.title("sambadotpy")
    window.geometry("200x500")
    IPConfigWindow(window).pack(fill="both", expand=True)
    window.mainloop()







   
        
        

