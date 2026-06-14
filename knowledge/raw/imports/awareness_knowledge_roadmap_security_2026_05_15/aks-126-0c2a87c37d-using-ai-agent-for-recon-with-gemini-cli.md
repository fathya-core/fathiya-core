# Using AI Agent for Recon with Gemini-Cli:

**Published:** 2026-01-05


## It can be installed on Kali Linux via the apt package `gemini-cli`


## Overview

Gemini-CLI is an open-source AI command-line interface that lets you use Google’s Gemini models directly from your terminal. It can be installed on Kali Linux via the apt package `gemini-cli`.

> Hey hackers 👋
> 
> I’m a passionate cybersecurity enthusiast and ethical hacker. I love solving CTFs on TryHackMe and Hack The Box, while also diving into recently discovered vulnerabilities to enhance my skills.

## 1\. Update System

Update package lists and upgrade existing packages:

sudo apt update  
sudo apt upgrade \-y

Install recommended prerequisites (Node.js is a dependency for Gemini-CLI through apt):

sudo apt install -y nodejs

## 2\. Install Gemini-CLI

On Kali Linux (2025.3 and later), the `gemini-cli` package is available directly from the Kali repositories:

sudo apt install gemini-cli

Verify installation:

gemini --help

If the CLI starts, installation succeeded. ([Kali Linux](https://www.kali.org/tools/gemini-cli/?utm_source=chatgpt.com))

## 3\. Gemini Authentication Methods

Gemini-CLI requires authentication before use. There are multiple methods:

*   **Google login (OAuth)**
*   **Gemini API key**
*   **Vertex AI / Google Cloud authentication**

This guide uses the **Gemini API key** method. ([Gemini CLI](https://geminicli.com/docs/get-started/authentication/?utm_source=chatgpt.com))

> Gemini-cli Interface

![Image](https://miro.medium.com/v2/resize:fit:700/1*5afuhXbUbRGTv2jlKnyeJg.png)

## 3.1 Generate an API Key

1.  Open Google AI Studio:[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2.  Create a new API key.
3.  Copy the key.

## 4\. Configure API Key

## 4.1 Set Environment Variable

In your terminal (bash):

export GEMINI\_API\_KEY="YOUR\_API\_KEY"

Replace `YOUR_API_KEY` with your actual key.

## 4.2 Persistent Configuration

To make it permanent (applies on every shell start):

echo 'export GEMINI\_API\_KEY="YOUR\_API\_KEY"' >> ~/.bashrc  
source ~/.bashrc

Confirm the variable is set:

echo $GEMINI\_API\_KEY

If it prints your key, it is configured correctly.

Alternative configuration methods: placing the key in a `.env` file at `~/.gemini/.env` (the CLI loads it automatically). ([Philschmid](https://www.philschmid.de/gemini-cli-cheatsheet?utm_source=chatgpt.com))

## 5\. Running Gemini-CLI

## 5.1 Basic Non-Interactive Prompt

You can run a single prompt directly:

gemini -p "Explain the difference between SQL injection and XSS"

or without `-p` (positional prompt):

gemini "Explain the difference between SQL injection and XSS"

## 5.2 Interactive Mode

Start an interactive session:

gemini use nmap  to scan host:<target\_domain>.com  
gemini use sql injection to login into host datebase and find vulnerabilities in host host:target\_domainlogin.php

Inside the CLI you can enter prompts and receive responses dynamically.

## 5.3 Model Selection

Specify a model (if supported):

gemini -m gemini-2.5\-pro -p "Generate a secure Python hash function"

Replace `gemini-2.5-pro` with another model if needed.

## 6\. Advanced Authentication (optional)

## 6.1 Vertex AI Authentication

If you use **Vertex AI** services instead of the API key, set additional environment variables:

export GOOGLE\_CLOUD\_PROJECT="your\_project\_id"  
export GOOGLE\_CLOUD\_LOCATION="your\_region"

Then authenticate with `gcloud`:

gcloud auth application-default login

Start Gemini-CLI and choose Vertex AI authentication mode. ([Gemini CLI](https://geminicli.com/docs/get-started/authentication/?utm_source=chatgpt.com))

## 7\. Configuration File

Gemini-CLI supports config files. Create directory:

mkdir -p ~/.config/gemini

Create a YAML config (optional):

\# ~/.config/gemini/config.yaml  
api\_key: "YOUR\_API\_KEY"  
model: "gemini-2.5-pro"  
temperature: 0.2  
max\_output\_tokens: 

Save and exit. The CLI may pick up settings from this file.

## 8\. Updating or Removing

## Update

sudo apt update  
sudo apt upgrade gemini\-cli

## Uninstall

sudo apt remove gemini-cli

## Advantages and Disadvantages of Gemini CLI for Hacking and Reconnaissance:-

Using **Gemini CLI** within Linux for hacking or reconnaissance has several notable advantages and disadvantages:

## Advantages Explained:

### Open Source

Being **open source** fosters a community environment conducive to collaboration and innovation. Users can contribute to its development, adding features and resolving bugs.

### Generous Free Tier

The **free tier** allows users to experiment and utilize the tool without financial commitment, making it an attractive option for beginners and ethical hackers.

### Versatile Coding Assistant

Gemini CLI serves as a **versatile assistant** that can handle a variety of tasks, making it a useful tool for both programming and hacking scenarios. It aids in automating repetitive tasks, thus enhancing productivity.

### Integration and Customization

Its facility for **integration** with other command-line tools enhances its efficacy, allowing users to create workflows tailored to their needs. This flexibility is particularly advantageous for those in hacking and reconnaissance.

### Large Context Window

The ability to manage a **large context window** enables users to maintain context over multiple commands or inputs, facilitating more complex projects.

## Disadvantages Explained:

### Reliability Issues

One of the main criticisms involves **reliability**. Users have reported that Gemini CLI may generate unexpected changes or fail to follow specific directives, which can be concerning during critical operations.

### Online Dependency

The requirement for an **online connection** may limit its use in scenarios where connectivity is an issue, such as in isolated network environments during penetration testing or reconnaissance.

### Lack of Complex Task Proficiency

While effective for basic tasks, Gemini CLI has been noted to **struggle with complex coding tasks**, making it less suitable for advanced hacking needs compared to more specialized tools.

### Still Under Development

As many features are still being completed, users could encounter **bugs or incomplete functionalities**. This can hinder the development process during critical tasks.

### Learning Curve

Despite its capabilities, there exists a **learning curve** associated with using Gemini CLI effectively. New users may require time to familiarize themselves with its features and command syntax.

> Thankyou for Reading…..