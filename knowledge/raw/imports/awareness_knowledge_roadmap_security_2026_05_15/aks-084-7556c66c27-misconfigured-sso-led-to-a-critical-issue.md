# Misconfigured SSO Led to a Critical Issue

**Published:** 2026-03-24


![Image](https://miro.medium.com/v2/resize:fit:700/0*RRjgk4NtrpgbEGF5)

*Photo by Kenny Eliason on Unsplash*

Hi everyone, in this article, I’ll walk through a recent penetration test I conducted against a web application. As usual, we’ll cover:

*   The application overview
*   The high-level architecture
*   The vulnerability
*   The exploit

This assessment was conducted as a black-box test, meaning no source code access, no architectural documentation, and no internal visibility — only what an external attacker would see.

## **Application overview**

Let’s refer to the company as **A.Corp**.

A.Corp maintained an internal web application used by **thousands of employees worldwide**. For security reasons, the application was only accessible to users connected to the **corporate network**.

The application supported **more than ten user roles**, including Basic, Regular, Manager, Senior Manager, Admin, Super Admin, and others. Each role had different levels of permissions and access to system functionality.

## High Level Architecture

Employees accessed the web application through **Single Sign-On (SSO)**. The internal SSO system was integrated with **Amazon Cognito**, effectively creating a tightly coupled authentication flow between the corporate identity provider and Cognito. AWS Sigv4 credentials returned by Amazon Cognito were saved in the browser’s Local Storage.

> Amazon Cognito acted as a federated identity broker, enabling users to authenticate once and access multiple applications using the same credentials. It also allowed the system to issue **temporary AWS credentials** for authenticated users.

The system exposed several categories of APIs:

*   **Cookie-authenticated APIs** — These APIs relied on session cookies for authentication and authorization.
*   **AWS SigV4–authenticated APIs** — These APIs required requests to be signed using **AWS Signature Version 4** credentials obtained through **Amazon Cognito**.
*   **Public or unauthenticated APIs** — Some endpoints did not require user authentication.

![Image](https://miro.medium.com/v2/resize:fit:700/1*hSy4ote4r-ZM3lZV-_PY6g.png)

*A high level architecture diagram.*

The above diagram shows a high level functioning of the workflow. The architecture is based on the APIs that were being called from the UI and the responses that were returned.

## The Vulnerability

I used Burp Autorize to automate the testing of the APIs that were being invoked from the UI. However, this was not possible for the APIs that used AWS Sigv4 because AWS Sigv4 headers that are sent with each API request are calculated on the fly. One cannot use the same AWS Sigv4 headers with different API calls.

After a while, I had been able to find the APIs which used AWS Sigv4 and were only callable through the Admin interface. I then went to the browser’s Local Storage, searched for AWS SigV4 credentials.

![Image](https://miro.medium.com/v2/resize:fit:700/1*c7cJ7PNNI39ELxEFHMAYzQ.png)

*AWS SigV4 credentials*

I exported these credentials as environment variables in my terminal just to play around with them.

![Image](https://miro.medium.com/v2/resize:fit:656/1*0vS6Eop9RkMuCnS_64hb1w.png)

The way to configure them in a bash terminal is as follows:

export AWS\_ACCESS\_KEY\_ID=  
export AWS\_SECRET\_ACCESS\_KEY=  
export AWS\_SESSION\_TOKEN=

You can then run the following command to see if the credentials were exported successfully and are valid

aws sts get\-caller\-identity

When I ran the above command, I could see the name of the role that was assigned with these AWS credentials.

## The Exploit

What’s more interesting is that when I exported the AWS Sigv4 credentials for other user accounts, and ran the `aws sts get-caller-identity` command, the same role name was reflected.

This means — All the users had the same authorization level. It was just hidden in plain sight for multiple years because:

*   Some APIs used session cookies (which were correctly configurd)
*   Some cookies did not require authentication
*   No one thought of testing APIs using AWS Sigv4

I then used `awscurl` to build API requests. `awscurl` is a handy pip pacakge that calculates Sigv4 headers on the fly and allows you to invoke APIs as if you are just using cURL.

I saw that I was able to call all the Admin and super admin APIs successfully even using the AWS Sigv4 credentials of the Basic User.

**Result? — A critical finding that was fixed in a week.**

Hope you enjoyed reading the article. Please consider subscribing and clapping for the article.

In case you are interested in CTF/THM/HTB writeups consider visiting my [YouTube](https://www.youtube.com/channel/UCnL50top2JtcuFVNdjDHiiw/) channel.