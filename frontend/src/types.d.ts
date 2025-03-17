import React from 'react'

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}

// This file is needed to resolve the TypeScript errors related to JSX elements
// without requiring explicit React imports in every file 