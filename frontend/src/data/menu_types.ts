export interface JsonSchema {
 type?:string;title?:string;description?:string;default?:unknown;enum?:unknown[];
 properties?:Record<string,JsonSchema>;required?:string[];anyOf?:JsonSchema[];
 items?:JsonSchema;minimum?:number;maximum?:number;$ref?:string;$defs?:Record<string,JsonSchema>;
 additionalProperties?:boolean|JsonSchema;
}
export interface BackendAction {
 id:string;name:string;menu:string;module:string;function:string;fields:string[];
 group:string;menu_id:string;defaults?:Record<string,string|number>;api:string;stop_api:string;
}
export interface BackendCommand {
 operation:string;methods:string[];module:string;function:string;group:string;menu:string;description:string;
 path_schema:JsonSchema;query_schema:JsonSchema;body_schema:JsonSchema;
}
export interface BackendMenuCatalog {
 groups:{id:string;title:string;menus:{id:string;title:string;operations:string[];views:string[];frontend:string;manager:string}[]}[];
 actions:BackendAction[];commands:BackendCommand[];
}
