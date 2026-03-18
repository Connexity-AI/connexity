// name items-update_item operation
const operationArg = {
  id: 'itemsUpdateItem',
  method: 'put',
  path: '/api/v1/items/{id}',
  operationId: 'items-update_item',
  description: 'Update an item.',
  summary: 'Update Item',
  tags: [ 'items' ],
  parameters: { path: { id: [Object] } },
  body: {
    mediaType: 'application/json',
    schema: { '$ref': '#/components/schemas/ItemUpdate' },
    required: true,
    type: 'json'
  },
  responses: {
    '200': { mediaType: 'application/json', schema: [Object] },
    '422': { mediaType: 'application/json', schema: [Object] }
  },
  security: [ { type: 'apiKey', in: 'cookie', name: 'auth_cookie' } ]
}
// finalName itemsUpdateItem
