---
name: form-dev
description: guidelines for creating forms with logic in separate hooks, server actions, and useMutation.
disable-model-invocation: true
---

# Form Development Pattern

This skill describes the project's standard pattern for developing forms. It ensures a clean separation of concerns between UI and business logic.

## Key Principles

1.  **Separation of Concerns**: The React component should be responsible only for User Interface (UI) elements and layout. All business logic, state management, and form handling must reside in a separate custom hook.
2.  **Logic Inversion**: Inject the logic from the hook into the component.
3.  **Data Fetching/Mutation**: Use `useMutation` from TanStack Query (TSQ) for form submissions and data updates.
4.  **Server Actions**: Perform database operations using Server Actions, passed as the `mutationFn` to `useMutation`.
5.  **Validation**: Implement validation on both the client (using `zod` and `react-hook-form`'s `zodResolver`) and the server (within the Server Action).
6.  **UI Components**: Use shadcn/ui components (Software-as-a-Service (SaaS) UI library) for all form elements to maintain consistency.

## Implementation Guide

### 1. Create a Custom Hook

The hook handles the form state, validation schema, and the mutation logic using TanStack Query (TSQ).

```typescript
// useMyForm.ts
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { myServerAction } from '@/lib/server-actions/my-actions';
import { toast } from '@/components/ui/sonner';

const formSchema = z.object({
  name: z.string().min(1, 'name is required'),
});

type FormValues = z.infer<typeof formSchema>;

export const useMyForm = () => {
  const queryClient = useQueryClient();
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: '' },
  });

  const { mutateAsync, isPending } = useMutation({
    mutationFn: myServerAction,
    onSuccess: () => {
      toast.success('saved successfully');
      form.reset();
      // queryClient.invalidateQueries({ queryKey: ['my-data'] });
    },
    onError: (error: Error) => {
      toast.error('failed to save');
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    await mutateAsync(values);
  });

  return { form, onSubmit, isPending };
};
```

### 2. Create the UI Component

The component receives props (if needed) and uses the hook to get the form state and handlers.

```tsx
// MyForm.tsx
'use client';

import { useMyForm } from './useMyForm';
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export function MyForm() {
  const { form, onSubmit, isPending } = useMyForm();

  return (
    <Form {...form}>
      <form onSubmit={onSubmit} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input {...field} placeholder="Enter name" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={isPending}>
          {isPending ? 'Saving...' : 'Save'}
        </Button>
      </form>
    </Form>
  );
}
```

### 3. Server-Side Execution & Validation

Mutation functions (Server Actions) must be organized within a `server/[module]/actions` folder. These actions act as entry points that call the business logic, often referred to as the "executor". Validation using Zod must occur again within the executor to ensure data integrity.

#### Example: Issue Update Flow

**1. Define the Schema**
`server/issues/schemas/index.ts`

```typescript
import { z } from 'zod';

export const updateIssueSchema = z.object({
  issueId: z.string().uuid(),
  title: z.string().min(1),
  summary: z.string().optional(),
});
```

**2. Create the Server Action**
`server/issues/actions/index.ts`

```typescript
'use server';

import { updateIssue } from '@/server/issues/update-issue';
import { UpdateIssueType } from '@/server/issues/types';

export const updateIssueAction = async (args: UpdateIssueType) => {
  return updateIssue(args);
};
```

**3. Implement the Executor (Business Logic)**
`server/issues/update-issue.ts`

The executor is wrapped with `withAuth` for security and `withValidation` to perform the Zod validation again on the server.

```typescript
import { withValidation } from '@/app/_common/_validation/with-validation';
import { updateIssueSchema } from '@/server/issues/schemas';
import { withAuth } from '@/app/_common/_auth/with-auth';
import { ApiError, CustomError } from '@/server/errors';
import { prisma } from '@/lib/prisma/prisma';

export const updateIssue = withAuth(
  withValidation(updateIssueSchema, async (args, user) => {
    try {
      const { issueId, title, summary } = args;

      // Business logic and database operations
      const updatedIssue = await prisma.issues.update({
        where: { id: issueId },
        data: {
          title,
          ...(summary !== undefined && { summary }),
        },
      });

      return updatedIssue;
    } catch (error) {
      if (error instanceof CustomError) {
        throw error;
      }
      throw new ApiError('Internal server error');
    }
  }),
);
```

## Best Practices

- Always use shadcn/ui components if possible.
- Always use `useMutation` for side effects (POST/PUT/DELETE).
- Use `toast` at client\components\UI\toast.tsx for feedback.
- Ensure `isPending` is used to disable the submit button and show loading states.
- Keep the hook file located close to the component file in a `hooks` subdirectory preferably.
- Use `queryClient.invalidateQueries` to refresh data after a successful mutation.
