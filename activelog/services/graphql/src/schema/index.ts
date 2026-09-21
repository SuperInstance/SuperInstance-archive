import { gql } from 'apollo-server-express';
import { buildFederatedSchema } from '@apollo/federation';
import { userTypeDefs } from './user';
import { fileTypeDefs } from './file';
import { videoTypeDefs } from './video';
import { pluginTypeDefs } from './plugin';
import { organizationTypeDefs } from './organization';
import { analyticsTypeDefs } from './analytics';
import { notificationTypeDefs } from './notification';
import { subscriptionTypeDefs } from './subscription';
import { resolvers } from '@/resolvers';

// Base schema with common scalars and directives
const baseTypeDefs = gql`
  scalar DateTime
  scalar JSON
  scalar Upload
  
  directive @auth(requires: Role = USER) on OBJECT | FIELD_DEFINITION
  directive @rateLimit(max: Int, window: Int) on FIELD_DEFINITION
  directive @complexity(value: Int) on FIELD_DEFINITION
  directive @cache(ttl: Int) on FIELD_DEFINITION
  directive @deprecated(reason: String) on FIELD_DEFINITION
  
  enum Role {
    USER
    ADMIN
    SUPER_ADMIN
    SERVICE
  }
  
  enum SortOrder {
    ASC
    DESC
  }
  
  interface Node {
    id: ID!
  }
  
  type PageInfo {
    hasNextPage: Boolean!
    hasPreviousPage: Boolean!
    startCursor: String
    endCursor: String
    totalCount: Int!
  }
  
  input PaginationInput {
    first: Int
    after: String
    last: Int
    before: String
  }
  
  input SortInput {
    field: String!
    order: SortOrder = ASC
  }
  
  type Error {
    message: String!
    code: String
    path: [String!]
    extensions: JSON
  }
  
  type MutationResponse {
    success: Boolean!
    message: String
    errors: [Error!]
  }
  
  # Health check query
  type Query {
    _service: _Service!
    health: HealthStatus!
    version: String!
  }
  
  type Mutation {
    _placeholder: Boolean
  }
  
  type Subscription {
    _placeholder: Boolean
  }
  
  type _Service {
    sdl: String!
  }
  
  type HealthStatus {
    status: String!
    timestamp: DateTime!
    services: [ServiceHealth!]!
  }
  
  type ServiceHealth {
    name: String!
    status: String!
    responseTime: Float
    error: String
  }
`;

// Combine all type definitions
export const typeDefs = [
  baseTypeDefs,
  userTypeDefs,
  fileTypeDefs,
  videoTypeDefs,
  pluginTypeDefs,
  organizationTypeDefs,
  analyticsTypeDefs,
  notificationTypeDefs,
  subscriptionTypeDefs
];

// Build federated schema
export const schema = buildFederatedSchema([
  {
    typeDefs,
    resolvers
  }
]);