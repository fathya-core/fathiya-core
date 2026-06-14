# WiFi Hacking 1O1, learn everything u need

**Published:** 2025-12-01


## Learn to attack WPA(2) networks! Ideally you’ll want a smartphone with you for this, preferably one that supports hosting wifi hotspots so you can follow along.


![Image](https://miro.medium.com/v2/resize:fit:700/1*QWj0gs72uV_NsaBNL_S1dw.jpeg)

## The basics — An Intro to WPA:

## Key Terms Explained

Understanding the terminology related to wireless networks is crucial, especially in the context of cybersecurity. Here’s a breakdown of the terms you’ve mentioned:

## SSID

**SSID** stands for **Service Set Identifier**. It is the name of a wireless network that users see when they attempt to connect. Each SSID is unique to a particular network, helping users identify and select the appropriate connection.

## ESSID

**ESSID** stands for **Extended Service Set Identifier**. This term applies to networks that may support multiple access points, such as those found in larger organizations (e.g., company offices). In tools like Aircrack, the ESSID typically refers to the network that you are attempting to attack.

## BSSID

**BSSID** refers to the **Basic Service Set Identifier**, which is the MAC (Media Access Control) address of a specific access point. This address uniquely identifies each access point on the network.

## WPA2-PSK

**WPA2-PSK** (Wi-Fi Protected Access II — Pre-Shared Key) is a security protocol used in wireless networks. It allows users to connect by entering a shared password, which is the same for all users on that network.

## WPA2-EAP

**WPA2-EAP** (Wi-Fi Protected Access II — Extensible Authentication Protocol) is a more secure authentication method used in enterprise environments. Users authenticate by providing a username and password, which are sent to a **RADIUS** server for validation.

## RADIUS

**RADIUS** (Remote Authentication Dial-In User Service) is a protocol used for authenticating clients. While it is commonly associated with Wi-Fi, it can also be used for other types of network access.

## 4-Way Handshake

The **4-way handshake** is a crucial aspect of WPA(2) authentication. It allows both the client and the access point (AP) to prove that they possess the correct encryption key while keeping the key itself secret. This process ensures that unauthorized users cannot easily access the network.

## Historical Context: WEP

**WEP** (Wired Equivalent Privacy) was a previous security standard for wireless networks. However, it is now considered insecure as vulnerabilities allow attackers to capture enough data packets to potentially guess the encryption key through statistical methods.

## Key Generation

WPA and WPA2 generate keys based on both the **ESSID** and the password for the network. The ESSID acts as a “salt,” which means that even if two networks use the same password, the keys will differ due to their unique SSIDs. This makes dictionary attacks more challenging, as attackers would need to precompute values for each access point’s MAC address rather than using a universal approach.

## You’re being watched — Capturing packets to attack:

## Attacking a WPA Network Using Aircrack-ng Suite

The Aircrack-ng suite is a powerful set of tools designed for network auditing and penetration testing, particularly for cracking WEP and WPA/WPA2 keys. Here’s a step-by-step guide to using Aircrack-ng to attack a WPA network.

## Prerequisites

1.  **Monitor Mode NIC**: Ensure you have a wireless network interface card (NIC) that supports monitor mode. This mode allows the card to capture all wireless traffic in the environment.
2.  **Operating System**: You can use Kali Linux, which comes with the Aircrack-ng suite pre-installed. Alternatively, it can be installed on other Linux distributions.

## Aircrack-ng Suite Components

The key tools you’ll utilize include:

*   **aircrack-ng**: Cracks WEP/WPA/WPA2 keys.
*   **airodump-ng**: Captures packets and displays information about the nearby wireless networks.
*   **airmon-ng**: Manages monitor mode on your NIC.

## Steps to Perform the Attack

## Step 1: Enable Monitor Mode

1.  **Open a terminal** in Kali Linux.
2.  **Identify your wireless card** using:

iwconfig

1.  **Enable monitor mode** with:Replace `<interface>` with your wireless card name (e.g., wlan0).

sudo airmon-ng start <interface\>

*   Step 2: Capture the 4-Way Handshake

1.  **Use airodump-ng** to scan for networks:

sudo airodump-ng <monitor-interface\>

Replace `<monitor-interface>` with the name of the monitor interface created earlier (e.g., wlan0mon). This will display available networks and connected clients.

1.  **Target your desired network** by using its BSSID and channel. Use a command similar to:

sudo airodump-ng --bssid <BSSID\> -c <channel\> -w <output\_file\> <monitor-interface\>

Replace `<BSSID>`, `<channel>`, and `<output_file>` accordingly.

## Step 3: Deauthenticate a Client

1.  **Deauthentication Attack**: To force a client to reconnect (and thereby capture the handshake), use aireplay-ng:Replace `<client_MAC>` with the MAC address of a connected client. The `10` indicates sending 10 deauth packets.

sudo aireplay-ng --deauth 10 -a <BSSID\> -c <client\_MAC\> <monitor-interface\>

## Step 4: Cracking the WPA Key

1.  **Once youcapture the handshake**, you can now use aircrack-ng to attempt to crack the password:Replace `<output_file>.cap` with the name of your capture file. This will use the Rockyou password list to attempt to find the password.

sudo aircrack-ng -w /usr/share/wordlists/rockyou.txt -b <BSSID> <output\_file>.cap

*   Generating Passwords

To generate random weak passwords from the Rockyou list, use:


head /usr/share/wordlists/rockyou.txt -n 10000 | shuf -n 5 -

This command provides five random passwords from the first 10,000 entries of the Rockyou list.

## Important Notes

*   **Ethical Considerations**: Always ensure you have permission to test the networks you are targeting. Unauthorized access to networks is illegal and unethical.
*   **Use Strong Passwords**: For educational purposes, utilize weak passwords when creating your targeted hotspot to see how vulnerabilities can be exploited.

By following these steps, you can effectively demonstrate the vulnerabilities associated with WPA networks and understand the process of penetration testing.

## Aircrack-ng — Let’s Get Cracking:-

## Cracking WPA Password Using Aircrack-ng

1.  **Use Aircrack-ng to crack the password** using the capture file:Replace `<capture_file>` with the name of your actual capture file.

aircrack-ng -w /usr/share/wordlists/rockyou.txt -b 02:1A:11:FF:D9:BD <capture\_file>.cap

Creating a Hashcat File

If you prefer using **Hashcat** for GPU acceleration:

1.  **Convert the capture file** into a Hashcat-compatible format using Airecrack-ng:

hashcat-utils -w <capture\_file\>.cap > <output\_hashcat\_file\>.hccapx

**Run Hashcat** using the output file:

hashcat -m 2500 -a 0 -w 3 <output\_hashcat\_file>.hccapx /usr/share/wordlists/rockyou.txt

*   `m 2500` specifies the WPA/WPA2 hash type.
*   `a 0` sets the attack mode to straight (dictionary attack).
*   `w 3` sets the workload profile for GPU acceleration.

Follow these instructions, and monitor the cracking process. If you’re not getting results within a few minutes, consider checking for common issues such as a weak dictionary or a slow system. Good luck!

> Thankyou For Reading..