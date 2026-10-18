from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

# Gateway tool names are "<target>___<tool>"; only these targets need to know who the caller is.
_CUSTOMER_SCOPED_TARGETS = ("orders___", "refunds___")


class CustomerContextHook(HookProvider):
    """Adds the caller's customer_id from agent state to customer-scoped tool calls, so the model never supplies it."""

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeToolCallEvent, self._inject_customer_id)

    def _inject_customer_id(self, event: BeforeToolCallEvent) -> None:
        if not event.tool_use["name"].startswith(_CUSTOMER_SCOPED_TARGETS):
            return
        customer_id = event.agent.state.get("customer_id")
        if not customer_id:
            # Fail closed: never let a customer-scoped call go out without an identity.
            event.cancel_tool = "No authenticated customer for this session."
            return
        # Overwrites anything the model put there, e.g. after a prompt injection.
        event.tool_use["input"]["customer_id"] = customer_id
