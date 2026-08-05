# When to Mock

Mock only a system boundary whose behavior cannot be made deterministic in the test. Prefer real in-memory or test adapters when they provide a faithful, fast boundary.

Mock at **system boundaries** only:

- External APIs (payment, email, etc.)
- Databases when a test database is unavailable or would make the test materially non-deterministic; otherwise prefer a test DB
- Time/randomness
- File system when isolation is required; otherwise prefer a temporary or in-memory filesystem

Keep these parts real:

- Your own classes/modules
- Internal collaborators
- Anything you control

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific functions for each external operation instead of one generic function with conditional logic:

```typescript
// GOOD: Each function is independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: Mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK approach means:
- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint

## Completion criterion

Mocking is complete when each mock represents an external or otherwise non-deterministic system boundary, the selected adapter preserves the contract needed by the test, and no internal collaborator is mocked merely for convenience.
