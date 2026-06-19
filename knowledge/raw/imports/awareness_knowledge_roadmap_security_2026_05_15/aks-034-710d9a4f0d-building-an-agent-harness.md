# Building an agent harness

**Published:** 2026-04-23


Prompt engineering, context engineering, and now harness engineering.

Prompt engineering entered the zeitgeist with the launch of ChatGPT in late 2022, defining the way that one effectively interacts with a large language model. Context engineering came to the fore last year in 2025, as builders sought to cram as much useful information into the prompt while staying within the bounds of context limits. Harness engineering has arisen as the hot topic this year, as builders optimize the scaffolding around the model to ensure that an agent processes a task request and returns the best response possible.

LangChain [wrote](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering) a post on improving deep agents with harness engineering, illustrating how to optimize agent performance by tweaking system prompts, tool use, and middleware, while keeping the underlying model the same. In particular, that latter middleware layer injected directory context for faster agent onboarding, validated outputs for quality verification, and enforced time budgets to ensure work completed in a reasonable time. This showed that agent builders can stand on the shoulders of frontier labs and produce even greater results, rather than simply waiting for the next model release for improving quality.

Birgitta Böckeler [wrote](https://martinfowler.com/articles/harness-engineering.html) a post on harness engineering for coding agent users, using a simple equation to define it: `agent = model + harness`. She explains the goals of a well-built harness as such:

> A well-built outer harness serves two goals: it increases the probability that the agent gets it right in the first place, and it provides a feedback loop that self-corrects as many issues as possible before they even reach human eyes.

AWS just [launched](https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/) a new managed agent harness for AgentCore, replacing the upfront agent build process with a simple config-based deployment.

In this blog post, I walk through my ongoing journey of building an agent harness inside my agent platform prototype, Loom. I also walk through my experience of integrating the new harness for AgentCore as another option for building agents.

### Getting under the hood in Loom

In my introductory [post](/introducing-loom-an-agent-platform-66e7db019cdb) for Loom, I outlined customer challenge #4, where software deployment requires rigorous testing, especially for AI-generated code. That is why I use a pre-written agent that essentially leverages feature flags for enabling integrations with memory, tools, and other agents. That allows for standard code scanning and avoids the need for an isolated environment for untrusted code execution.

![Image](https://miro.medium.com/v2/resize:fit:700/0*5RGbm4oTcAH6_G10.png)

*Pre-written agent build via configuration injection*

In order to do this, I inject an `AGENT_CONFIG_JSON` environment variable with the following payload:

{  
  "system\_prompt": "persona, instructions, guidelines",  
  "model\_id": "us.amazon.nova-2-lite-v1:0",  
  "max\_tokens": 16384,  
  "integrations": {  
    "mcp\_servers": \[  
      {  
        "name": "utilities",  
        "enabled": true,  
        "transport": "streamable\_http",  
        "endpoint\_url": "https://example.heeki.cloud/mcp",  
        "auth": {  
          "type": "oauth2",  
          "credential\_provider\_name": "<agentcore-credential-provider-for-utilities>",  
          "well\_known\_endpoint": "https://cognito-idp.<region>.amazonaws.com/<cognito-pool-id>/.well-known/openid-configuration",  
          "scopes": "utilities/invoke ..."  
        }  
      }  
    \],  
    "a2a\_agents": \[  
      {  
        "name": "agentforce-assistant",  
        "enabled": true,  
        "endpoint\_url": "https://api.salesforce.com/einstein/ai-agent/a2a/<agent-identifier>",  
        "auth": {  
          "type": "oauth2",  
          "credential\_provider\_name": "<agentcore-credential-provider-for-agentforce-assistant>",  
          "well\_known\_endpoint": "https://<organization-id>.develop.my.salesforce.com/.well-known/openid-configuration"  
        }  
      }  
    \],  
    "memory": {  
      "enabled": true,  
      "resources": \[  
        {  
          "name": "demo\_employee\_assistant",  
          "memory\_id": "demo\_employee\_assistant-RNDrSHC2P5",  
          "arn": "arn:aws:bedrock-agentcore:<region>:<account-id>:memory/demo\_employee\_assistant-RNDrSHC2P5"  
        }  
      \]  
    }  
  }  
}

The `system_prompt` parameter combines the separate inputs for persona, instructions, and guidelines for initializing the agent.

agent = Agent(  
    system\_prompt=config.system\_prompt,  
    model=model,  
    tools=tools,  
    hooks=hooks,  

The `model_id` and `max_tokens` parameters are used for configuring the Bedrock model. In the future, I plan to update this to support other 3p model providers.

model = BedrockModel(  
    model\_id=config.model\_id,  
    max\_tokens=config.max\_tokens,  
    streaming=True,  

The `integrations.mcp_servers` and `integrations.a2a_agents` parameters are used for conditionally defining the tool list for the agent. I slightly simplified the code below for brevity.

if config.integrations.mcp\_servers:  
    enabled\_servers = \[s for s in config.integrations.mcp\_servers if s.enabled\]  
    if enabled\_servers:  
        mcp\_clients = build\_mcp\_clients(config.integrations.mcp\_servers)  
        tools.extend(mcp\_clients)  
        logger.info("Loaded %d MCP tool client(s)", len(mcp\_clients))  
  
if config.integrations.a2a\_agents:  
    enabled\_agents = \[a for a in config.integrations.a2a\_agents if a.enabled\]  
    if enabled\_agents:  
        a2a\_clients = create\_a2a\_clients(config.integrations.a2a\_agents)  
        if a2a\_clients:  
            tools.extend(a2a\_clients)  
            logger.info("Loaded %d A2A client(s)", len(a2a\_clients))

The `integrations.memory` parameter is used for defining whether a hook is required for interacting with memory during lifecycle events.

if config.integrations.memory.enabled:  
    memory\_store\_id = None  
    if config.integrations.memory.resources:  
        memory\_store\_id = config.integrations.memory.resources\[0\].memory\_id  
    memory\_hook = MemoryHook(memory\_store\_id=memory\_store\_id)  
    hooks.append(memory\_hook)  
    logger.info("Enabled AgentCore Memory hook (store\_id=%s)", memory\_store\_id)

This approach allows for agent configuration at deploy time, optionally setting each of those configurations, depending on the requirements of the use case.

But what if I want to make changes to the agent configuration at runtime? It is common to allow end users to choose their preferred model. It is also common to add tool integrations while interacting with the agent.

### Considering deploy time versus run time configuration

So how does that work? The deployment configurations act as the default setting while runtime configurations allow the user to override those defaults with whatever the user chooses.

![Image](https://miro.medium.com/v2/resize:fit:700/1*Hf23TqEA1soZJVeOh8HP9g.png)

*Default deployment configs and override runtime configs*

The invoke payload includes options for overriding the model and adding connectors (tools or other agents) at runtime. That is [defined](https://github.com/heeki/loom/blob/bd0234ae69983429fa4734c7383880522c4ac41b/backend/app/routers/invocations.py#L46) using the `InvokeRequest` class.

{  
  "prompt": "What is the weather in New York?",  
  "session\_id": "existing-session-id-or-null",  
  "model\_id": "us.amazon.nova-2-lite-v1:0",  
  "credential\_id": 1,  
  "bearer\_token": "<your-bearer-token>",  
  "connector\_ids": \[3, 7\]  
}

*   `prompt` (required): user message
*   `session_id`: reuse an existing session or omit to create a new one
*   `model_id`: override agent’s default model, must be in `allowed_model_ids`
*   `credential_id`: internal authorizer identifier for token generation
*   `bearer_token`: manually generated bearer token
*   `connector_ids`: internal connector ids to attach for this invocation

For example, I can configure a number of allowed models for a particular agent. Those are the ones from which the end user can select.

![Image](https://miro.medium.com/v2/resize:fit:700/1*seQ54t7ePlHsl12TJk28wA.png)

*Administrator view for selecting allowed models for the end user*

Then the end user can go and select the preferred model.

![Image](https://miro.medium.com/v2/resize:fit:700/1*S19af0TtBUT6EfGQszFHWA.png)

*End user view for selecting the preferred model*

If the user chooses an alternate model, then that is passed via the invoke request. The agent then [uses](https://github.com/heeki/loom/blob/bd0234ae69983429fa4734c7383880522c4ac41b/agents/strands_agent/src/handler.py#L173) the selected model.

### Adding tools at runtime

Updating the model at runtime is fairly easy, as that is just an additional parameter that is handled in the agent. Adding new tools at runtime has a twist that requires some additional care.

![Image](https://miro.medium.com/v2/resize:fit:700/1*7vNcqMYo1RPwZUmkOIdl7Q.png)

*Runtime connector enablement view*

In my introductory post, I outlined customer challenge #6, where identity propagation needs to be managed through delegated actor chains. I had proposed a simplification by intentionally constraining the architecture to a single hop. This is the approach that many agentic user interfaces take today, where users can enable a connection on-demand.

The key benefit to that approach is capturing user credentials when the user toggles on a new connector. I conjecture that capturing credentials at this point imposes the _least_ amount of user consent fatigue, since there is high intentionality on the user’s part for interacting with that integration.

Waiting to capture credentials until they are actually needed doesn’t make sense, as the user could have walked away for a long running task. For example, it would be the same experience of kicking off a long-running task in Claude Code, stepping away, and then returning to find that it paused execution 10 seconds after you left, requesting permission to navigate a directory or to read a file.

Note that this is a _simplification_ not a solution for agent identity and permissions delegation. RFC 8693 is a token exchange proposal that helps with delegation by carrying information in an actor claim in the JWT.

In the example screenshot above, I setup an account with exa.ai/mcp and created an API key, which gives me 1000 requests per month in the free tier. Good enough for basic prototyping. While I can setup the MCP server at the admin level, doing so would effectively set that API key for every single user that enables that connector. In some scenarios, that is fine. In other scenarios, it makes sense to have per-user API keys.

![Image](https://miro.medium.com/v2/resize:fit:700/1*yVz0ImakrH4CkBL5l5PBWg.png)

*Per-user API key for MCP connectors*

I went this latter route. So when the user enables the connector, a pop-up dialog asks the user to enter a personal API key. That personal key is then used when making requests to the MCP server.

Note that at the time of this writing, AgentCore credential providers do not yet support per-user API keys. As such, I ended up injecting the header via the agent request, rather than using the credential provider.

### Integrating the managed agent harness into Loom

A fair amount of iteration went into the implementation to get to the current state. On one hand, building my own agent harness taught me a lot and gave me a ton of flexibility, e.g., adding custom logging for telemetry and cost estimation. On the other hand, that was perhaps more engineering than one may care to invest into an agent platform.

Harness for AgentCore just launched to simplify the deployment of agents and integration with various context providers.

What I particularly love about the managed agent harness is the fact that it includes both deployment time and runtime options for model selection and tool integration. For example, at deployment, I have the following options, using the CLI as an example of configuration possibilities:

aws bedrock-agentcore-control create-harness \\  
  --region us-east-1 \\  
  --harness-name "loom-harness-example" \\  
  --execution-role-arn "arn:aws:iam::${ACCOUNT\_ID}:role/loom-harness-role" \\  
  --system-prompt "persona, instructions, guidelines" \\  
  --model "us.amazon.nova-2-lite-v1:0" \\  
  --max-iterations 75 \\  
  --max-tokens 16384 \\  
  --tools '\[{"type": "remote\_mcp", "name": "exa", "config": {"remoteMcp": {"url": "https://mcp.exa.ai/mcp"}}}\]' \\  
  --memory '{"optionalValue": {"agentCoreMemoryConfiguration": {"arn": "arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT\_ID}:memory/${MEMORY\_ID}"}}}'

Similar, at runtime, I have the following options to override the the model and tool options, as follows:

response = client.invoke\_harness(  
    harnessArn=HARNESS\_ARN,  
    runtimeSessionId=SESSION\_ID,  
    messages=\[  
        {  
            "role": "user",  
            "content": \[  
                {"text": "What's the weather in New York City?"}  
            \],  
        }  
    \],  
    model={  
        "bedrockModelConfig": {  
            "modelId": "us.anthropic.claude-sonnet-4-6"  
        }  
    },  
    tools=\[  
        {  
            "type": "remote\_mcp",  
            "name": "exa",  
            "config": {"remoteMcp": {"url": "https://mcp.exa.ai/mcp"}}  
        }  
    \]  

This is a lot of time saved for a fully managed, serverless experience for building agents! It is also delightfully fast in the deployment experience. While it takes roughly 1 minute with my custom agent, the harness deployment takes about 20 seconds!

![Image](https://miro.medium.com/v2/resize:fit:1000/1*u5ysGyymP1UJVTE28V7B6Q.png)

*Agent created in Loom using the new harness in AgentCore*

I also already integrated the managed agent harness into Loom and have that available in [release 1.3.0](https://github.com/heeki/loom/releases/tag/v1.3.0).

Note that you need to upgrade to `boto3` version `1.42.94` to get access to the new harness methods.

Note that you need to add custom authorization headers for remote MCP servers that require OAuth2 access tokens, as it seems like credential providers are not yet supported at the time of this writing.

{  
  "harnessArn": "arn:aws:bedrock-agentcore:<region>:<account-id>:harness/<harness-id>",  
  "runtimeSessionId": "552bb0ed-f268-46e6-9db9-53df37b149f0",  
  "messages": \[  
    {  
      "role": "user",  
      "content": \[  
        {  
          "text": "What's the weather in New York City?"  
        }  
      \]  
    }  
  \],  
  "tools": \[  
    {  
      "type": "remote\_mcp",  
      "name": "utilities",  
      "config": {  
        "remoteMcp": {  
          "url": "https://<mcp-server-endpoint>/mcp",  
          "headers": {  
            "Authorization": "Bearer <access-token>"  
          }  
        }  
      }  
    }  
  \],  
  "actorId": "admin"  
}

### Conclusion

Harness engineering is en vogue as organizations optimize agents for both efficiency and response quality. Building an agent harness is not impossible but does require some careful consideration.

AWS just launched a fully managed agent harness for simplifying the experience of building and deploying your agents in the cloud. The AWS console has a playground experience that makes testing super easy.

Happy building!

### Resources

*   [https://martinfowler.com/articles/harness-engineering.html](https://martinfowler.com/articles/harness-engineering.html)
*   [https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering)
*   [https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/](https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/)
*   [https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html)
*   [https://x.com/aparnadhinak/status/2016915570503938452](https://x.com/aparnadhinak/status/2016915570503938452)