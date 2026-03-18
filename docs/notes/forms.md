```ts
Forms with React 19 and Next.js - leerob

https://www.youtube.com/watch?v=KhO4VjaYSXU
https://v0.app/chat/form-with-use-action-state-CiFWYqPHKvT?b=b_0v5ES6AiBeq
// client component that calls action
'use client'
const [state, action, isPending] = useActionState(submitAddress, initialState)
<form action={action} className="space-y-6" autoComplete="on">

// conclusion
form component client, everything above server components
---------------
// validate and submit, working
https://github.com/orgs/react-hook-form/discussions/11832#discussioncomment-11832211
https://dev.to/emmanuel_xs/how-to-use-react-hook-form-with-useactionstate-hook-in-nextjs15-1hja

<form action={formAction} onSubmit={validateAndSubmit} className="space-y-6" />

const validateAndSubmit = (event: FormEvent<HTMLFormElement>) => {
event.preventDefault();

form.handleSubmit(() => {
    const formElement = event.target as HTMLFormElement;
    const formData = new FormData(formElement);

    startTransition(() => {
    formAction(formData);
    form.reset();
    });
})(event);
};
----------
// when to reset form after submit and when not
Create user → reset after success
Update user, login, register → DO NOT reset // anywhere with redirect
```
