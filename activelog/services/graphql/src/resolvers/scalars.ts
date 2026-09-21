import { GraphQLScalarType, Kind } from 'graphql';
import { GraphQLUpload } from 'graphql-upload-minimal';

export const scalarResolvers = {
  // DateTime scalar
  DateTime: new GraphQLScalarType({
    name: 'DateTime',
    description: 'Date and time in ISO 8601 format',
    serialize(value: Date | string | number): string {
      if (value instanceof Date) {
        return value.toISOString();
      }
      if (typeof value === 'string' || typeof value === 'number') {
        return new Date(value).toISOString();
      }
      throw new Error(`Value is not a valid DateTime: ${value}`);
    },
    parseValue(value: string): Date {
      if (typeof value !== 'string') {
        throw new Error(`Value is not a string: ${value}`);
      }
      const date = new Date(value);
      if (isNaN(date.getTime())) {
        throw new Error(`Value is not a valid DateTime: ${value}`);
      }
      return date;
    },
    parseLiteral(ast): Date {
      if (ast.kind !== Kind.STRING) {
        throw new Error(`Can only parse strings to dates but got a: ${ast.kind}`);
      }
      const date = new Date(ast.value);
      if (isNaN(date.getTime())) {
        throw new Error(`Value is not a valid DateTime: ${ast.value}`);
      }
      return date;
    }
  }),

  // JSON scalar
  JSON: new GraphQLScalarType({
    name: 'JSON',
    description: 'Arbitrary JSON object',
    serialize(value: any): any {
      return value;
    },
    parseValue(value: any): any {
      return value;
    },
    parseLiteral(ast): any {
      switch (ast.kind) {
        case Kind.STRING:
          try {
            return JSON.parse(ast.value);
          } catch {
            return ast.value;
          }
        case Kind.OBJECT:
          return ast.fields.reduce((obj: any, field: any) => {
            obj[field.name.value] = this.parseLiteral(field.value);
            return obj;
          }, {});
        case Kind.LIST:
          return ast.values.map(this.parseLiteral);
        case Kind.INT:
          return parseInt(ast.value, 10);
        case Kind.FLOAT:
          return parseFloat(ast.value);
        case Kind.BOOLEAN:
          return ast.value;
        case Kind.NULL:
          return null;
        default:
          return null;
      }
    }
  }),

  // Upload scalar
  Upload: GraphQLUpload
};