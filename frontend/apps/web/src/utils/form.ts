export const objectToFormData = (obj: Record<string, string | Blob>): FormData => {
  const formData = new FormData();

  for (const [key, value] of Object.entries(obj)) {
    formData.append(key, value);
  }

  return formData;
};
