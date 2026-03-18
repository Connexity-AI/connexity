import { z } from 'zod';

// Todo: must match Pydantic in backend/app/models.py

// login
export const loginFormSchema = z.object({
  username: z
    .string()
    .min(1, { message: 'Email is required' })
    .pipe(z.email({ message: 'Invalid email address' })),
  password: z
    .string()
    .min(1, { message: 'Password is required' })
    .min(6, { message: 'Password must be at least 6 characters long' }),
});

// register
export const registerFormSchema = z
  .object({
    email: z
      .string()
      .min(1, { message: 'Email is required' })
      .pipe(z.email({ message: 'Invalid email address' })),
    full_name: z
      .string()
      .min(2, { message: 'Full name must be at least 2 characters long' })
      .optional()
      .or(z.literal('')),
    password: z
      .string()
      .min(1, { message: 'Password is required' })
      .min(6, { message: 'Password must be at least 6 characters long' }),
    confirm_password: z
      .string()
      .min(1, { message: 'Password confirmation is required' })
      .min(6, { message: 'Password must be at least 6 characters long' }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

// profile
export const profileUpdateSchema = z.object({
  user_id: z.string(),
  email: z
    .string()
    .min(1, { message: 'Email is required' })
    .pipe(z.email({ message: 'Invalid email address' })),
  full_name: z.string().min(2, { message: 'Full name must be at least 2 characters long' }),
});

export const profilePasswordUpdateSchema = z
  .object({
    current_password: z
      .string()
      .min(1, { message: 'Current password is required' })
      .min(6, { message: 'Password must be at least 6 characters long' }),

    new_password: z
      .string()
      .min(1, { message: 'New password is required' })
      .min(6, { message: 'New password must be at least 6 characters long' }),

    confirm_password: z
      .string()
      .min(1, { message: 'Password confirmation is required' })
      .min(6, { message: 'New password must be at least 6 characters long' }),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });
