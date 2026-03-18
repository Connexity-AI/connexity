import { z } from 'zod';

import {
  loginFormSchema,
  profilePasswordUpdateSchema,
  profileUpdateSchema,
  registerFormSchema,
} from '@/schemas/forms';

// login
export type LoginFormValues = z.output<typeof loginFormSchema>;
export type LoginFormKeys = keyof LoginFormValues;

// register
export type RegisterFormValues = z.output<typeof registerFormSchema>;
export type RegisterFormKeys = keyof RegisterFormValues;

// profile
export type ProfileUpdateFormValues = z.output<typeof profileUpdateSchema>;
export type ProfileUpdateFormKeys = keyof ProfileUpdateFormValues;

export type ProfilePasswordUpdateFormValues = z.output<typeof profilePasswordUpdateSchema>;
export type ProfilePasswordUpdateFormKeys = keyof ProfilePasswordUpdateFormValues;
