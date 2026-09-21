import { ApolloServerPlugin, GraphQLRequestListener } from '@apollo/server';
import { GraphQLError } from 'graphql';
import {
  getComplexity,
  createComplexityLimitRule,
  fieldExtensionsEstimator,
  simpleEstimator
} from 'graphql-query-complexity';

const DEFAULT_MAX_COMPLEXITY = 1000;
const ADMIN_MAX_COMPLEXITY = 5000;

export const complexityPlugin = (): ApolloServerPlugin => {
  return {
    requestDidStart(): GraphQLRequestListener<any> {
      return {
        didResolveOperation({ request, document, operationName, contextValue }) {
          // Get user from context
          const user = contextValue.user;
          
          // Determine max complexity based on user role
          let maxComplexity = DEFAULT_MAX_COMPLEXITY;
          if (user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN') {
            maxComplexity = ADMIN_MAX_COMPLEXITY;
          }
          
          // Calculate query complexity
          const complexity = getComplexity({
            schema: request.schema,
            operationName,
            query: document,
            variables: request.variables,
            estimators: [
              // Use field extensions (@complexity directive)
              fieldExtensionsEstimator(),
              // Fallback to simple estimator
              simpleEstimator({ maximumDepth: 10 })
            ]
          });
          
          // Log high complexity queries
          if (complexity > maxComplexity * 0.8) {
            console.warn(`High complexity query detected:`, {
              complexity,
              maxComplexity,
              operationName,
              userId: user?.id,
              query: request.query
            });
          }
          
          // Reject if complexity exceeds limit
          if (complexity > maxComplexity) {
            throw new GraphQLError(
              `Query complexity ${complexity} exceeds maximum allowed complexity ${maxComplexity}`,
              {
                extensions: {
                  code: 'QUERY_COMPLEXITY_TOO_HIGH',
                  complexity,
                  maxComplexity
                }
              }
            );
          }
          
          // Add complexity info to response extensions
          return {
            willSendResponse(requestContext) {
              if (requestContext.response.http?.body && 'singleResult' in requestContext.response.http.body) {
                const result = requestContext.response.http.body.singleResult;
                if (result.extensions) {
                  result.extensions.complexity = {
                    value: complexity,
                    maximum: maxComplexity
                  };
                } else {
                  result.extensions = {
                    complexity: {
                      value: complexity,
                      maximum: maxComplexity
                    }
                  };
                }
              }
            }
          };
        },
        
        validationDidStart() {
          return {
            willValidate({ document, contextValue, operationName }) {
              // Add complexity validation rule
              const user = contextValue.user;
              let maxComplexity = DEFAULT_MAX_COMPLEXITY;
              
              if (user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN') {
                maxComplexity = ADMIN_MAX_COMPLEXITY;
              }
              
              return [
                createComplexityLimitRule(maxComplexity, {
                  estimators: [
                    fieldExtensionsEstimator(),
                    simpleEstimator({ maximumDepth: 10 })
                  ],
                  onComplete: (complexity) => {
                    console.log(`Query complexity: ${complexity}/${maxComplexity}`);
                  }
                })
              ];
            }
          };
        }
      };
    }
  };
};