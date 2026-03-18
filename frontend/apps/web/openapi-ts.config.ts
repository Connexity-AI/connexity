import { defineConfig } from '@hey-api/openapi-ts';

type HeyApiConfig = ReturnType<typeof defineConfig>;

/**
 *
 * @example {
 * id: 'itemsUpdateItem',
 * operationId: 'items-update_item',
 * tags: [ 'items' ],
 * }
 */
type Operation = {
  id?: string;
  operationId?: string;
  tags?: string[];
  [key: string]: unknown;
};

/**
 * Remove service (resource) prefix from method names.
 * Cannot be imported, must be in same file
 * @example itemsUpdateItem -> updateItem
 */
const methodNameBuilder = (operation: Operation) => {
  // no operation.name prop
  const initialName: string = operation.id ?? operation.operationId ?? 'unknownOperation';
  let name = initialName;

  // no operation.service prop, use first tag as the service/resource name
  const service: string = operation.tags?.[0] ?? '';

  // Remove service prefix from name
  if (service && name.toLowerCase().startsWith(service.toLowerCase())) {
    name = name.slice(service.length);
  }

  name = name
    // Remove '_', '-', ' ' separators
    // and convert the following char to camelCase
    // or remove the separator if the separator is at the end
    .replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ''))
    // remove non-alphanumeric characters
    .replace(/[^a-zA-Z0-9]/g, '');

  // Lowercase first character
  const finalName = name.charAt(0).toLowerCase() + name.slice(1);

  // Note: keep it for debugging
  console.log('initialName:', initialName, '-> finalName:', finalName);

  return finalName;
};

const config: HeyApiConfig = defineConfig({
  input: './openapi.json',
  output: {
    format: 'prettier',
    lint: 'eslint',
    path: './src/client',
    importFileExtension: null,
  },
  exportSchemas: true, // backend models types
  plugins: [
    // Note: order matters
    {
      name: '@hey-api/typescript',
      enums: 'javascript', // const objects instead of enums
    },
    '@hey-api/schemas', // default json, req.body, '{"username":"abc","password":"123"}'
    {
      // must pin to "@hey-api/openapi-ts": "0.88.0",
      name: '@hey-api/sdk',
      asClass: true, // UsersService.readUserMe(), 'true' doesn't allow tree-shaking
      classNameBuilder: '{{name}}Service', // class Users -> UsersService
      // @ts-expect-error @hey-api/openapi-ts doesn't export types
      methodNameBuilder, // usersReadUserMe -> readUserMe
    },
    {
      name: '@hey-api/client-next',
      // relative from src/client/ folder
      runtimeConfigPath: '../lib/hey-api', // sets API_URL, auth...
    },
  ],
});

export default config;
