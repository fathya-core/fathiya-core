# Complete Guide to Penetration Testing Domains: Web, Network, Cloud, Mobile & More

**Published:** 2025-12-07


## Understanding the Different Specializations in Cybersecurity Testing and How to Choose Your Path


Penetration testing isn’t a one-size-fits-all discipline. As someone who’s spent considerable time working in cybersecurity and experimenting across various domains, I’ve learned that the field is remarkably diverse. Each domain requires distinct skills, tools and methodologies. Whether you’re considering a career in pentesting or looking to expand your expertise, understanding these different areas is crucial for success.

![Image](https://miro.medium.com/v2/resize:fit:700/0*ZWSffvNTRGIpQZoS.png)

Let’s dive deep into the major domains of penetration testing, exploring what makes each unique and what you need to know to get started.

## Web Application Penetration Testing: The Most In-Demand Skill

Web application penetration testing focuses on identifying and exploiting vulnerabilities in web-based applications. With virtually every business operating online, this has become one of the most sought-after skills in cybersecurity.

## Understanding Web Application Architecture

Web applications follow a three-tier architecture: the presentation tier (frontend), application tier (backend) and database tier. To test effectively, you need to understand how these components interact. This means being familiar with HTTP/HTTPS protocols, HTML, CSS, JavaScript for frontend analysis, server-side languages like PHP, Python, or Java and database technologies including SQL and NoSQL.

Unlike traditional network testing, web app pentesting requires deep knowledge of how applications handle user input, manage sessions and process data. The attack surface is unique because you’re not just looking at network configurations you’re examining application logic, business workflows and data handling practices.

## Critical Web Application Vulnerabilities

**SQL Injection** remains one of the most severe vulnerabilities. When applications fail to properly sanitize user input used in database queries, attackers can manipulate those queries to extract, modify, or delete data. Similarly, Command Injection vulnerabilities allow attackers to execute system commands on the server, potentially compromising the entire system.

**Authentication and Session Management** weaknesses can lead to unauthorized access. Common issues include weak password policies, improper session token management and authentication bypass vulnerabilities. These flaws can give attackers complete control over user accounts.

**Cross-Site Scripting (XSS)** occurs when applications fail to properly sanitize user input that gets displayed to other users. These vulnerabilities are particularly dangerous because they allow attackers to execute malicious scripts in victims’ browsers, leading to session hijacking, credential theft, or malware distribution.

## Essential Tools for Web Application Testing

Proxy tools like Burp Suite Professional and OWASP ZAP are fundamental for intercepting and analyzing web traffic. These tools let you capture requests, modify parameters and analyze responses to identify vulnerabilities. Browser developer tools are equally crucial for understanding client-side behavior and examining JavaScript execution.

Scripting languages, particularly Python, are valuable for automating repetitive tasks and creating custom exploitation tools. The security community favors Python due to its extensive library support and ease of use.

## The Professional Approach

Web application penetration testing isn’t just about finding vulnerabilities — it’s about helping organizations improve their security posture. Professional testers identify security issues and provide actionable recommendations for fixing them and preventing similar problems in the future. This requires understanding business logic, thinking like both a developer and an attacker and communicating findings effectively.

## Network Security Penetration Testing: Building the Foundation

Network penetration testing evaluates the security of an organization’s entire network infrastructure, including routers, switches, firewalls, servers and endpoints. This domain forms the foundation that many other testing disciplines build upon.

## Understanding Network Architecture

Networks consist of various interconnected components, each potentially harboring vulnerabilities that could compromise the entire system. Understanding how these components interact and communicate is fundamental to conducting effective penetration tests. You need to grasp network protocols like TCP/IP, UDP, ICMP and application-layer protocols such as HTTP, FTP and SSH.

## The Network Testing Methodology

Network penetration testing follows a systematic approach. It begins with reconnaissance — collecting key network information like IP ranges, domain names and system details through both passive methods (searching public records) and active methods (scanning the network directly).

Next comes network scanning to find active systems, open ports and running services. Tools like Nmap help map out the network and identify potential weak points by examining which ports are open or closed and what services are running on them.

The vulnerability assessment phase involves looking for weak spots in services and systems. While automated scanners like Nessus and OpenVAS are helpful, manual verification is essential to confirm findings and eliminate false positives.

During the exploitation phase, testers attempt to leverage discovered vulnerabilities to access systems or obtain sensitive data, always being careful not to cause damage. For example, discovering an unpatched service might lead to testing for buffer overflow vulnerabilities, or finding an open FTP service could prompt checking whether anonymous login is enabled.

Post-exploitation activities demonstrate how far an attacker could go — obtaining higher access levels and moving laterally through the network. This shows clients exactly how an attacker could progress through their systems.

## Common Network Vulnerabilities

Network environments frequently contain several security weaknesses:

*   **Misconfigured Services**: Improperly configured network services, default credentials and unnecessary open ports that provide unauthorized access
*   **Unpatched Systems**: Systems running outdated software versions with known security vulnerabilities
*   **Weak Authentication**: Poor password policies, lack of multi-factor authentication and insecure password storage
*   **Insecure Protocols**: Use of deprecated or unencrypted protocols like FTP, Telnet or HTTP instead of their secure alternatives
*   **Network Segmentation Issues**: Inadequate network segregation allowing lateral movement between different security zones
*   **Exposed Management Interfaces**: Administrative interfaces accessible from unauthorized networks or the internet
*   **Missing Security Controls**: Absence of essential security measures like firewalls, IDS/IPS systems or proper access controls

## Specialized Area: Wireless Network Testing

Wireless network testing is a specialized aspect of network penetration testing. It involves assessing WiFi network security, testing encryption protocols (WEP, WPA, WPA2, WPA3), analyzing authentication mechanisms and identifying rogue access points. Tools like the Aircrack-ng suite are commonly used for wireless assessments.

## Critical Success Factors

Common pitfalls include rushing through reconnaissance without proper attention to detail, relying excessively on automated tools without understanding their limitations and neglecting manual validation of findings. Maintaining consistent communication with the client throughout the testing process is essential. Regular status updates, prompt notification of critical findings and clear documentation help ensure alignment on objectives and expectations.

## Cloud Security Penetration Testing: Securing the Modern Infrastructure

As businesses rapidly migrate to cloud platforms, cloud security penetration testing has become critical. This domain differs significantly from traditional testing and requires specialized knowledge.

## Understanding Cloud Service Models

Before diving into cloud testing, you need to understand the three basic cloud service models:

*   **Infrastructure as a Service (IaaS)**: Testing infrastructure components like virtual machines, networks and storage
*   **Platform as a Service (PaaS)**: Focusing on platform-level security, including development frameworks and databases
*   **Software as a Service (SaaS)**: Dealing primarily with application-level security and data protection mechanisms

Each model presents unique security challenges and requires different testing approaches.

## Key Differences from Traditional Testing

The main distinction lies in the shared responsibility model, where security responsibilities are divided between the cloud service provider and the customer. As a penetration tester, you must be clear about which components you can test and which are off-limits according to the cloud provider’s acceptable use policies.

Another crucial difference is the dynamic nature of cloud environments. Resources can be created, modified, or destroyed automatically, making it essential to adapt your testing approach accordingly. Cloud environments also implement complex access controls and identity management systems that require specialized testing methodologies.

## Essential Skills for Cloud Testing

Proficiency in cloud penetration testing requires expertise in several areas. Strong understanding of major cloud platforms like AWS, Azure, or Google Cloud Platform is essential, including knowledge of their security features, native tools and common misconfigurations.

Familiarity with Infrastructure as Code (IaC) and automation tools is valuable since many cloud deployments utilize these technologies. Knowledge of containerization technologies like Docker and Kubernetes is increasingly important as modern cloud applications are often container-based. Understanding API security testing is crucial since most cloud services interact through APIs.

## Cloud Penetration Testing Methodology

The assessment begins with reconnaissance and enumeration of cloud resources, identifying all active services, storage buckets, databases and other cloud components. Cloud-specific scanners and enumeration scripts significantly aid this process.

Access control testing assesses the implementation of Identity and Access Management (IAM) policies, examining for overly permissive roles, misconfigured security groups and weak authentication mechanisms.

Configuration assessment scrutinizes cloud services for security misconfigurations like publicly accessible storage buckets or unencrypted databases.

Network security testing in cloud environments involves reviewing virtual network configurations, security groups and network access controls.

Data security testing evaluates the implementation of encryption, data loss prevention (DLP) and key management practices.

Application security testing examines cloud-native applications, checking for vulnerabilities in application code and APIs.

## Common Cloud Vulnerabilities

Cloud environments often suffer from specific vulnerabilities:

*   Misconfigured storage buckets exposing sensitive data
*   Excessive permissions and inadequate IAM policies leading to privilege escalation
*   Insecure API implementations allowing unauthorized access or data exposure
*   Insufficient logging and monitoring making incident detection difficult
*   Container security issues like running containers with root privileges or using outdated base images
*   Inadequate network segmentation and overly permissive security groups
*   Lack of encryption for data at rest and in transit

## Cloud Testing Tools

Cloud testing requires a combination of cloud-native and traditional security tools. Cloud providers offer their own security assessment tools like AWS Inspector and Azure Security Center. Third-party tools like CloudSploit, Scout Suite and Prowler provide automated assessments. For container security, tools like Clair, Trivy and Anchore are essential. API testing tools such as Postman and Burp Suite help evaluate API security. Traditional tools like Nmap and Metasploit remain relevant but must be used carefully to comply with provider policies.

## Mobile Security Penetration Testing: Securing Devices in Your Pocket

Mobile security testing focuses on identifying vulnerabilities in mobile applications and devices. With businesses increasingly relying on mobile devices for critical operations, this domain has become essential.

## Why Mobile Security Matters

Mobile devices handle sensitive company data, customer details and business systems, making their security a top priority. Several factors drive the importance of mobile security:

*   **BYOD Policies**: Companies must secure employee personal devices accessing work resources
*   **Data Breach Costs**: Security failures lead to fines, legal issues and reputation damage
*   **Remote Work Revolution**: More remote workers mean more mobile devices connecting to company networks
*   **Compliance Requirements**: Laws require strict data protection and privacy measures
*   **Advanced Threats**: Mobile devices face attacks from malware, phishing and new security exploits

## Understanding the Mobile Attack Surface

The mobile attack surface differs considerably from traditional web applications or desktop software. Mobile applications often store sensitive data locally, communicate with multiple backend services and interact with various hardware components. This creates unique security challenges and potential entry points.

Key areas of concern include local data storage, network communication, inter-process communication (IPC) and platform-specific security mechanisms. Understanding these components is essential for effective testing.

## Setting Up Your Testing Environment

Proper mobile testing requires both physical devices and emulators/simulators. For Android testing, access to both rooted and non-rooted devices is necessary. For iOS, having both jailbroken and non-jailbroken devices is beneficial.

Essential tools include:

*   Mobile device management tools like Android Debug Bridge (ADB)
*   Reverse engineering tools such as JADX and Ghidra
*   Network analysis tools like Burp Suite Mobile Assistant
*   Platform-specific debugging tools
*   Mobile framework testing tools like Frida and Objection

## Android Security Testing

Android testing begins with understanding the application’s structure. Android applications are distributed as APK files containing the application’s code, resources and manifest file. The manifest file declares the application’s permissions, components and security settings.

Static analysis involves decompiling APKs and examining source code for security issues. This can reveal hardcoded credentials, insecure data storage practices and logic flaws. Tools like JADX can decompile Android applications into readable Java code.

Dynamic analysis involves running the application and observing its behavior in real-time, including monitoring network traffic, analyzing file system operations and testing runtime behavior. Frida is particularly useful for dynamic analysis, allowing you to hook into application functions and modify their behavior.

## iOS Security Testing

iOS applications operate in a more restricted environment but aren’t immune to security issues. iOS apps are distributed as IPA files, which are encrypted by default, so testing often requires decrypting these files first.

The iOS security model is built around app sandboxing, code signing and various platform security features. Understanding these mechanisms is crucial for effective testing. Tools like Objection and Frida can bypass certain security controls during testing.

When testing iOS applications, pay special attention to:

*   Keychain usage and data protection
*   Certificate pinning implementation
*   Local data storage practices
*   URL scheme handling
*   Touch ID/Face ID implementation

## Common Mobile Vulnerabilities

Mobile-specific issues to watch for include:

**Insecure Data Storage**: Sensitive information stored in plaintext or with weak encryption, including authentication tokens, personal information, or business data.

**Weak Network Security**: Applications not properly validating SSL/TLS certificates, implementing certificate pinning incorrectly, or sending sensitive data over insecure channels. Man-in-the-middle attacks remain relevant though they require special setup.

**Client-Side Injection**: SQL injection in local databases, JavaScript injection in WebViews and other injection points specific to mobile platforms.

## Advanced Mobile Testing Techniques

Advanced techniques include analyzing native code components, reviewing custom encryption implementations and testing complex authentication mechanisms. Runtime manipulation using tools like Frida can reveal how applications handle security controls, including bypassing root detection, modifying in-app purchase validation, or understanding anti-debugging measures.

## Physical Security Penetration Testing: Beyond the Digital Realm

Physical security testing evaluates the effectiveness of physical security controls, barriers and procedures protecting an organization’s physical assets. This often-overlooked domain is crucial because the best digital security means nothing if someone can simply walk into your server room.

## Scope of Physical Security Testing

Physical security testing encompasses various aspects of an organization’s physical infrastructure, including building perimeters, security checkpoints, entry points like doors and windows, restricted areas and sensitive asset storage locations. The primary goal is to exploit gaps in security controls and bypass them to gain unauthorized physical access.

## Key Components of Physical Testing

**External Security Assessment** begins with evaluating the outer perimeter of a facility, including examining fences, gates, walls and other physical barriers. Testers assess lighting conditions, surveillance camera placement and coverage and potential blind spots. They also evaluate the effectiveness of perimeter intrusion detection systems and identify potential entry points that might be overlooked.

**Access Control Systems** are critical components comprising key card systems, biometric readers, PIN pads and mechanical locks. Pentesters assess both the technical security of these systems and their practical implementation. This might involve testing for tailgating vulnerabilities, checking if doors are properly secured and evaluating visitor management systems.

**Security Personnel** play a vital role in physical security. Testers evaluate their adherence to security protocols, response to suspicious activities and enforcement of access control policies. This often involves social engineering attempts to test how well staff follow security procedures and verify visitors’ credentials.

## Physical Testing Methodology

The initial phase involves gathering information about the target facility through open-source intelligence (OSINT), studying publicly available information, satellite imagery, social media and other relevant sources. Detailed observations of the target facility are conducted, documenting security camera locations, guard patrol patterns and employee behaviors. This often involves multiple visits at different times to understand how security measures vary throughout the day.

With proper authorization, testers attempt to bypass security controls using various techniques, including lock picking, cloning access cards, tailgating, or social engineering. All attempts are carefully documented, including both successful and unsuccessful approaches.

## Common Physical Testing Techniques

Social engineering plays a crucial role in physical security testing. Testers might pose as delivery personnel, maintenance workers, or other legitimate visitors to test how well staff verify credentials and follow security procedures. This helps identify weaknesses in human security controls and training needs.

Testing often includes evaluating the security of physical locks, examining the types of locks used, their installation quality and their resistance to various bypass techniques. Lock manipulation should only be performed by qualified professionals with proper authorization during real assessments.

Modern physical security incorporates electronic systems that are also evaluated. This could include testing RFID cards for cloning vulnerabilities, examining the security of access control panels and assessing the integration of various security systems.

## Legal and Ethical Considerations

Physical security testing must always be conducted within legal and ethical boundaries. Obtaining proper written authorization is mandatory and testers must stay within a clearly defined scope. Privacy laws must be respected and activities must not pose risk to people or property.

Testers must always carry their authorization letter during engagements. This document should detail the scope of work, authorization from the client, emergency contacts and testing timeframes. If confronted by security personnel or law enforcement, this documentation can quickly validate the legitimate nature of the testing activities and prevent unnecessary escalation or legal complications.

## Social Engineering: Testing the Human Element

Social engineering focuses on the human element of cybersecurity, exploiting human psychology and behavior patterns to gain unauthorized access to systems, networks, or physical locations. This recognizes that humans are often the weakest link in the security chain.

## The Psychology Behind Social Engineering

Social engineering relies on key psychological principles that make humans vulnerable to manipulation:

*   **Authority**: People tend to respond automatically to authority figures
*   **Urgency**: Creates pressure that can lead to hasty decisions
*   **Fear**: Can paralyze critical thinking
*   **Curiosity**: Compels people to click suspicious links or open malicious attachments
*   **Trust**: Can be exploited through relationship building and manipulation

Social engineers exploit these natural human tendencies to bypass security measures and obtain sensitive information.

## Common Social Engineering Techniques

**Phishing** remains the most prevalent attack, involving deceptive emails that appear to come from legitimate sources, attempting to trick recipients into revealing sensitive information or taking harmful actions. Spear phishing takes this further by targeting specific individuals with personalized content based on detailed research.

**Pretexting** involves creating a fabricated scenario to obtain information or access. For example, a social engineer might pose as an IT technician needing system credentials for “maintenance.” This technique requires detailed preparation and research to create convincing scenarios.

**Baiting** exploits human curiosity by leaving infected USB drives or other malicious devices in locations where targets might find and use them. This technique plays on people’s natural tendency to investigate unknown items.

## Physical Social Engineering

While many social engineering attacks occur digitally, physical social engineering is equally important in penetration testing. This involves gaining unauthorized physical access to facilities through various techniques such as tailgating (following authorized personnel through secure doors), impersonating delivery personnel, or claiming to be a new employee who forgot their access card.

Physical social engineering requires strong interpersonal skills, quick thinking and the ability to maintain composure under pressure. Successful physical penetration testers often combine multiple techniques, such as using fake credentials while maintaining a confident demeanor and professional appearance.

## Conducting Social Engineering Assessments

A social engineering assessment begins with meticulous reconnaissance of the target environment. This involves systematically gathering detailed information about the target organization, including its organizational structure, key personnel, internal processes and existing security practices through open-source intelligence (OSINT) methodologies.

Professional penetration testers utilize various public information sources, including social media platforms, company websites, professional networking sites, public records databases and industry publications. These sources reveal invaluable insights about the organization’s operations, helping craft highly convincing and contextually appropriate attack scenarios.

Following intelligence gathering, penetration testers carefully analyze the collected information to develop sophisticated and targeted attack scenarios. These scenarios are meticulously crafted based on the organization’s identified vulnerabilities, specific security objectives and real-world risk factors. The developed scenarios must balance being sufficiently challenging to test the organization’s security posture while remaining realistic and representative of actual threats.

Before proceeding with any testing activities, it is absolutely essential to maintain detailed documentation of all planned activities and secure explicit written authorization from appropriate organizational stakeholders.

## Ethical Considerations and Responsibilities

Social engineering tests must be conducted ethically and professionally. This requires proper authorization, protection of sensitive information discovered during testing and safeguards to prevent harm to the organization or its employees. Penetration testers must be ready to reveal their identity immediately if any situation risks becoming dangerous or harmful.

Social engineering demands special consideration during penetration testing for several reasons:

*   It involves manipulating human emotions and psychology, which may cause psychological distress if not handled carefully
*   It involves accessing or attempting to access personal information, raising important privacy and ethical concerns
*   Unsuccessful or successful social engineering attempts can erode workplace trust and damage professional relationships

Social engineering tests can expose organizations to legal liability without proper authorization and documentation. The manipulation of trust can have lasting negative effects on organizational culture and employee morale. For these reasons, social engineering assessments must be carefully planned, executed under strict ethical guidelines and include appropriate support mechanisms for affected employees.

## Reverse Engineering: Understanding Software from the Inside Out

Reverse engineering is the process of analyzing and understanding how software, systems, or applications work by examining their components, structure and functionality. For penetration testers, this skill enables the identification of vulnerabilities, understanding of security mechanisms and development of effective exploitation techniques.

## What Makes Reverse Engineering Different

Unlike forward engineering, where you start with requirements and create a product, reverse engineering begins with the final product and works backward to understand its implementation and code. This is particularly valuable when source code or documentation is unavailable, which is often the case during security assessments.

## Essential Knowledge for Reverse Engineering

To effectively reverse engineer software or mobile applications, a solid foundation in multiple technical areas is essential:

*   Deep understanding of programming languages relevant to the target platform (C/C++, Java, Swift, Kotlin)
*   Knowledge of assembly language and computer architecture
*   Operating system internals, including memory management, process handling and system calls
*   For mobile applications, familiarity with platform-specific architectures (iOS/Android), their security models and common protection mechanisms
*   Understanding of common software design patterns, data structures and algorithms
*   Knowledge of networking protocols and API communication

## Fundamentals of Reverse Engineering

At its core, reverse engineering demands a comprehensive understanding of computer architecture, assembly language and how programs execute at the machine level. When a program undergoes compilation, human-readable source code is transformed into machine code — precise sequences of instructions that the computer’s processor can interpret and execute directly.

As someone beginning in reverse engineering, you need to familiarize yourself with fundamental concepts that form the backbone of program execution. Critical is developing a deep understanding of memory layout, which encompasses various crucial components including the stack, heap and different segments of a program, each serving distinct purposes in program execution.

The stack handles the management of function calls and local variables in a highly organized manner, maintaining the proper execution flow. Meanwhile, the heap takes responsibility for dynamic memory allocation, allowing programs to request and utilize memory resources as needed during runtime.

## Essential Reverse Engineering Tools

You’ll need to become proficient with several categories of tools:

**Disassemblers** like IDA Pro, Ghidra, or Radare2 are fundamental. These tools convert machine code back into assembly language, making it more readable for analysis.

**Debuggers** such as GDB, WinDbg or x64dbg are equally important, allowing you to examine program execution in real-time, set breakpoints and analyze memory contents.

**Decompilers** attempt to reconstruct high-level source code from compiled binaries. While not perfect, they can significantly speed up the analysis process by providing a more intuitive view of the program’s logic. Examples include DNSpy, ILSpy and JADX.

## Static vs. Dynamic Analysis Approaches

Reverse engineering typically involves two main approaches:

**Static Analysis** involves examining the program without executing it. This includes studying the program’s structure, identifying functions and variables and understanding the overall flow of the application. It’s valuable for getting a broad overview and identifying potential areas of interest.

**Dynamic Analysis** involves running the program and observing its behavior in real-time. This includes monitoring memory usage, tracking function calls and analyzing program flow during execution. This analysis is particularly useful for understanding complex algorithms, anti-debugging techniques and encryption implementations.

## Common Reverse Engineering Scenarios

As a penetration tester, you’ll encounter various scenarios where reverse engineering skills are invaluable:

**Malware Analysis**: Understanding how malicious software operates can help develop better defenses, attacks and improve evasion techniques.

**Authentication Bypass**: Reverse engineering can reveal weak validation checks or hardcoded credentials.

**Protocol Analysis**: Many applications use custom protocols for communication. Understanding these protocols through reverse engineering can reveal security flaws or enable the development of custom tools for testing.

## Advanced Challenges

As you progress in reverse engineering, you’ll encounter more complex challenges. Anti-reverse engineering techniques like code obfuscation, packed executables and anti-debugging measures are common in modern software. Understanding these protection mechanisms and how to bypass them becomes crucial.

Different platforms and architectures present unique challenges. Mobile applications often use different protection mechanisms than desktop applications. Similarly, embedded systems may require specialized knowledge and tools for effective analysis.

## Choosing Your Penetration Testing Path

Each penetration testing domain offers unique challenges and opportunities. Web application testing provides a great entry point with high demand across industries. Network testing builds foundational skills applicable to other domains. Cloud testing is perfect for those interested in modern infrastructure and emerging technologies. Mobile testing suits those interested in app development and mobile platforms. Physical and social engineering testing are ideal for those with strong interpersonal skills and interest in the human element of security.

The truth is, most successful penetration testers develop expertise in multiple domains. The skills from one area often complement another — network knowledge enhances cloud testing, reverse engineering improves mobile testing and understanding web applications helps with overall security assessments.

## Final Thoughts

Penetration testing is a vast and evolving field. Each domain requires dedication, continuous learning and hands-on practice. The key is to start somewhere, build your foundational skills and gradually expand into other areas as your expertise grows.

Remember that penetration testing isn’t just about breaking things — it’s about helping organizations improve their security posture. Whether you specialize in web applications, networks, cloud infrastructure, mobile devices, physical security, social engineering, or reverse engineering, your ultimate goal is to make systems and organizations more secure.

The cybersecurity landscape continues to evolve, bringing new challenges and opportunities. By understanding these different domains and continuously developing your skills, you’ll be well-positioned to build a rewarding career in penetration testing and make a meaningful impact in the field of cybersecurity.

## About Me

Hi, I’m [**Dhanush Nehru**](https://youtu.be/UaNYT-5fLRw?si=jQEyC_m4AFKGn0lt) an Engineer and Content Creator. I document my journey through articles and videos, sharing real-world insights about DevOps, automation, security, cloud engineering and more.

_You can_ [**_support me_**](https://buymeacoffee.com/dhanushnehru) **_/_** [**_sponsor me_**](https://github.com/sponsors/DhanushNehru) _or follow my work via_ [**_X_**](https://x.com/Dhanush_Nehru) _,_ [**_Instagram_**](https://www.instagram.com/dhanush_nehru/)_,_ [**_Github_**](https://github.com/DhanushNehru/) _or_ [**_Youtube_**](https://www.youtube.com/@dhanushnehru?sub_confirmation=1)_._

![Dhanush N](https://miro.medium.com/v2/resize:fill:40:40/1*g-aoUi88UKMpAxezY9NcmQ.png)

[Dhanush N](/?source=post_page-----66834579378b---------------------------------------)

## Cybersecurity

[View list](/list/cybersecurity-22cd940844c3?source=post_page-----66834579378b---------------------------------------)

60 stories

![Image](https://miro.medium.com/v2/resize:fill:388:388/1*H-X9Faz4lXIFt2UUwGYFOw.png)

![Image](https://miro.medium.com/v2/resize:fill:388:388/0*KYQODJsgH2nduH4A.jpg)

![Image](https://miro.medium.com/v2/resize:fill:388:388/1*eXjDBKbpkgFbfc71VyPffA.png)

![Dhanush N](https://miro.medium.com/v2/resize:fill:40:40/1*g-aoUi88UKMpAxezY9NcmQ.png)

[Dhanush N](/?source=post_page-----66834579378b---------------------------------------)

## DevOps

[View list](/list/devops-f81a76cfa7f2?source=post_page-----66834579378b---------------------------------------)

25 stories

![Image](https://miro.medium.com/v2/da:true/resize:fill:388:388/0*zGKvFD_W6-u6qdt0)

![Image](https://miro.medium.com/v2/resize:fill:388:388/0*cfxI0v3jBwmHHna2.png)

![Image](https://miro.medium.com/v2/resize:fill:388:388/0*vNt-ECYA25Tv0_uC.png)

![Dhanush N](https://miro.medium.com/v2/resize:fill:40:40/1*g-aoUi88UKMpAxezY9NcmQ.png)

[Dhanush N](/?source=post_page-----66834579378b---------------------------------------)

## All About AI

[View list](/list/all-about-ai-c6288641eead?source=post_page-----66834579378b---------------------------------------)

24 stories

![Image](https://miro.medium.com/v2/resize:fill:388:388/1*yrt0OcyB9xB2Qvgy6DRTxA.png)

![Image](https://miro.medium.com/v2/resize:fill:388:388/1*kMIY3YycsXaf_OFdRA66Sg.png)

![Image](https://miro.medium.com/v2/resize:fill:388:388/1*czDMx9xNSxeqJLF2zdhVuQ.png)