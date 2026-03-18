```ts

// errors
// 1. throw message instead of returning {data, error}
const result = await ItemsService.readItems({
    throwOnError: true, // causes rejected Promise, not Error, ErrorBoundary cant handle
    baseUrl: 'http://localhost:8000/404', // force error
});
// then it returns this
const result: {
    data: ItemsPublic;
    response: Response;
}
// must rewrite error.message logging in ErrorBoundary for proper logging // NO
// cant handle async errors, Promise instead of error.message
class ErrorBoundary extends Component<Props, State> {

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }; // this
  }
}

// 2. return and rethrow message
const isError = isErrorApiResult(result);
if (isError) throw new Error(getApiErrorMessage(result.error));

// Todo: custom error (exception) classes

// force error
UsersService.readUsers({
  baseUrl: 'http://localhost:8000/404',
});
// or
const [currentUserResult, usersResult] = await Promise.all([
  UsersService.readUserMe(),
  Promise.reject(new Error("Forced readUsers error")),
]);
-------------
// number of lines in working directory - uncommitted
git diff --shortstat HEAD
git diff --stat HEAD
// in latest commit
git diff --shortstat HEAD~..HEAD
// last 2
git diff --shortstat HEAD~2..HEAD
----
diff - only lines
show - author, date, message, lines
------------
// idea for article RHF with server action before form submit
validateAndSubmit() ...
--------
export type UsersDeleteUserMeResponses = {
  /**
   * Successful Response
   */
  200: Message;
};
result.data is 200, tj. Message
response.200 === response.data
```
