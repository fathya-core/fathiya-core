# How I Used OSINT to Gather Information Like a Hacker

**Published:** 2026-04-10


## I found my company’s exposed secrets in two hours. No hacking required.


![Image](https://miro.medium.com/v2/resize:fit:700/0*T66AP5gW-2a2tepu.jpg)

*OSINT*

I wanted to see what an attacker could learn about my organization without ever touching our network. No exploits, no passwords, no illegal activity. Just a browser and public search engines.

Within two hours, I had a list of employee emails, internal server names, and a forgotten PDF containing network diagrams. All of it was legally available online. Our team had published it themselves without realizing.

This is OSINT: open-source intelligence. And it is how hackers build their attack maps before ever sending a single packet.

## Starting With What You Already Publish

I began on our own company website. I viewed the page source and found developer comments revealing internal file paths and staging server URLs. One comment read, “**<!—remove debug=true before launch →**” still there after two years.

Then I checked image metadata. A photo of our team’s offsite contained GPS coordinates and the camera model. That alone told an attacker where our employees gathered and what devices they use.

Everything I found was public. We just never thought to look.

## Harvesting Emails Without Breaking Rules

Employee email addresses are everywhere. I searched LinkedIn for our company name and collected job titles and names. Then I guessed the email format, first.last@company.com, and tested it on a password reset form. The system did not send a reset email, but it confirmed the account existed.

This is not hacking. It is how web forms work. The defensive lesson? Use email confirmation messages that do not reveal whether an account exists.

## The GitHub Goldmine

I searched GitHub for our company domain. A developer had pushed a configuration file with internal API endpoints and a commented‑out admin password. The repository was public for three years.

I downloaded the file, verified the endpoints, and showed leadership. They were horrified. We rotated credentials and set up automated scanning for secrets in public repos.

You can do this too. Search for your company name on GitHub right now.

## Job Postings Leak Everything

Job descriptions tell attackers what technology you use. “**Senior AWS Engineer**” means cloud infrastructure. “**Salesforce Administrator**” means customer data in Salesforce. Each listing narrows the attack surface.

I collected five job postings and built a technology stack map. Then I looked for known vulnerabilities in those specific tools. Attackers do this daily. The fix? Use generic descriptions and avoid naming specific software versions.

## Social Media and Physical Clues

I scrolled through our company’s Instagram and LinkedIn photos. One picture showed an employee’s badge on a desk. The badge format, color, logo placement, and card type reveal the access control system we use.

Another photo had a whiteboard in the background with part of a network diagram visible. Attackers zoom in on these details. Encourage your team to blur sensitive information before posting. Or better, create a policy against photographing internal spaces.

## Google Dorks for Defenders

Advanced search operators find exposed files. I used `site:ourcompany.com ext: pdf` and found an internal security policy document with server names. `intitle: index of` revealed an open directory of log files from an old server.

These techniques are legal. Google indexes everything. Your job is to find what is public and remove it.

## Protecting Your Human Perimeter

I searched for employee names on social media. One engineer posted about a conference, including his hotel and travel dates. That is enough for a targeted phishing or physical pretexting attack.

Train your team to limit public sharing of work‑related locations, schedules, and internal projects.

## What You Should Do Today

Run a simple OSINT audit on your own organization. Search your domain on GitHub. Check your website’s source code. Look at your social media photos.

Make a list of every piece of exposed information. Then close the gaps. The attackers are already doing this. Now you can too defensively.

What is the most surprising thing you have found about your own company online? Share in the comments. Clap if you are auditing your digital footprint today, and follow for more defensive security techniques.