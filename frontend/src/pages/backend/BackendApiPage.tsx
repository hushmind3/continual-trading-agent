import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import './BackendApiPage.css';

export function BackendApiPage() {
  return <section className="backend-api-page" aria-label="백엔드 API 문서">
    <SwaggerUI url="/openapi.json" {...{ validatorUrl: null }} docExpansion="list"
      defaultModelsExpandDepth={-1} displayRequestDuration />
  </section>;
}
