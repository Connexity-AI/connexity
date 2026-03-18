export const removeLeadingSlash = (path: string) => path.replace(/^\/+/g, '');

export const removeTrailingSlash = (path: string) => path.replace(/\/+$/g, '');

export const removeLeadingAndTrailingSlashes = (path: string) => path.replace(/^\/+|\/+$/g, '');

type ParsedPage = {
  isValidPage: boolean;
  currentPage: number;
};

export const parsePage = (page: unknown): ParsedPage => {
  const DEFAULT_CURRENT_PAGE = 1;
  const INVALID_RESULT: ParsedPage = { isValidPage: false, currentPage: DEFAULT_CURRENT_PAGE };

  // Convert whatever comes in into a number once.
  const parsedPage = Number(page);

  let result: ParsedPage = INVALID_RESULT;

  switch (true) {
    // Valid page
    // undefined for '/' no param
    case page === undefined:
      result = { isValidPage: true, currentPage: DEFAULT_CURRENT_PAGE };
      break;

    // Invalid pages
    case Number.isNaN(parsedPage): //  Not convertible to number (NaN)
    case !Number.isInteger(parsedPage): //  Not an integer (e.g., 1.5, "2.3")
    case parsedPage === 0: //  Page is 0 (explicitly invalid)
    case parsedPage < 0: //  Negative pages (invalid)
      result = INVALID_RESULT;
      break;

    // Valid pages
    // (positive integers: 1, 2, 3, ...)
    case parsedPage >= 1:
      result = { isValidPage: true, currentPage: parsedPage };
      break;

    // Fallback (should never happen, but keeps switch exhaustive)
    default:
      result = INVALID_RESULT;
      break;
  }

  return result;
};

type PageBoundsArgs = {
  currentPage: number;
  totalItems: number;
  totalPages: number;
};

export const isPageOutOfBoundsFn = ({
  currentPage,
  totalItems,
  totalPages,
}: PageBoundsArgs): boolean => {
  const result =
    totalItems === 0
      ? // for 0 items, only allow page 1
        currentPage !== 1
      : currentPage < 1 || currentPage > totalPages;

  return result;
};
