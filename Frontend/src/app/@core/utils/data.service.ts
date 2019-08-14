import {Injectable} from '@angular/core';
import {HttpService} from '../../config/http.service';
import {HttpClient} from '@angular/common/http';

@Injectable()
export class DataService extends  HttpService<any> {

  constructor(public http: HttpClient) {
    super(http, {
      path: '',
    });
  }

}
